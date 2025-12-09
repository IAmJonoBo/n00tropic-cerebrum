#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "${ROOT_DIR}"

if ! command -v gh >/dev/null 2>&1; then
	echo "GitHub CLI 'gh' is required. Install it or run this from GitHub Actions with gh available."
	exit 1
fi

DESCRIPTION="Finds candidate branches for deletion and merges automerge-labeled PRs"
USAGE="Usage: $0 [--days N] [--auto-delete] (defaults: days=30, auto-delete=false)"

days=30
auto_delete=0
while [[ $# -gt 0 ]]; do
	case "$1" in
	--days)
		days="$2"
		shift 2
		;;
	--auto-delete)
		auto_delete=1
		shift
		;;
	-h | --help)
		echo "$USAGE"
		exit 0
		;;
	*)
		echo "Unknown arg: $1" >&2
		echo "$USAGE" >&2
		exit 1
		;;
	esac
done

echo "[wrangle-branches] Using days=${days}, auto_delete=${auto_delete}"

# Owner and repo detection
origin=$(git remote get-url origin || true)
if [[ -z $origin ]]; then
	echo "Could not determine origin remote URL" >&2
	exit 1
fi
owner=$(echo "$origin" | sed -E 's#.*github.com[:/]+([^/]+)/([^/]+).git#\1#')
repo=$(echo "$origin" | sed -E 's#.*github.com[:/]+([^/]+)/([^/]+).git#\2#')
echo "Repository: ${owner}/${repo}"

now_ts=$(date -u +%s)
cutoff=$((now_ts - days * 24 * 60 * 60))

echo "Merging automerge PRs (if mergeable)"
# use existing script to safely merge automerge PRs
bash .dev/automation/scripts/merge-to-minimal-set.sh || true

echo "Collecting branches candidate for deletion"
candidates=()
page=1
while true; do
	branches_json=$(gh api -X GET "/repos/${owner}/${repo}/branches?per_page=100&page=${page}" || true)
	if [[ -z $branches_json || $branches_json == "[]" ]]; then
		break
	fi
	# iterate branches
	for branch in $(printf '%s' "$branches_json" | jq -r '.[].name'); do
		# skip protected / default branches
		if [[ $branch == "main" || $branch == "master" || $branch =~ ^release|^rc|^hotfix ]]; then
			continue
		fi
		# get commit date for branch
		branch_info=$(gh api "/repos/${owner}/${repo}/branches/${branch}")
		commit_date=$(printf '%s' "$branch_info" | jq -r '.commit.commit.committer.date')
		commit_ts=$(
			python3 - <<PY
from datetime import datetime, timezone
import sys
try:
    ts=datetime.fromisoformat('''${commit_date}'''.replace('Z','+00:00')).timestamp()
    print(int(ts))
except Exception as e:
    print(0)
    sys.exit(0)
PY
		)
		if [[ $commit_ts -le $cutoff ]]; then
			# check if branch has open PR or closed merged PR
			prs=$(gh pr list --head "${owner}:${branch}" --state all --json number,state,mergedAt -q '.[] | {number, state, mergedAt}')
			merged=false
			if [[ -n $prs ]]; then
				state_val=$(echo "$prs" | jq -r '.[0].state' 2>/dev/null || echo "")
				mergedAt_val=$(echo "$prs" | jq -r '.[0].mergedAt' 2>/dev/null || echo "")
				if [[ $state_val == "MERGED" || $mergedAt_val != "null" && -n $mergedAt_val ]]; then
					merged=true
				fi
			fi
			if [[ $merged == true ]]; then
				candidates+=("${branch}|merged")
			else
				# no PR merged: propose deletion if no PRs exist
				pr_count=$(gh pr list --head "${owner}:${branch}" --state all --json number -q '. | length')
				if [[ $pr_count -eq 0 ]]; then
					candidates+=("${branch}|no_pr")
				fi
			fi
		fi
	done
	# paginate
	if printf '%s' "$branches_json" | jq -e 'length == 100' >/dev/null 2>&1; then
		page=$((page + 1))
	else
		break
	fi
done

if [[ ${#candidates[@]} -eq 0 ]]; then
	echo "No candidate branches found for deletion"
	exit 0
fi

echo "Found ${#candidates[@]} candidates:"
for c in "${candidates[@]}"; do
	echo " - $c"
done

issue_body="# Branch cleanup candidates\nThe following branches were detected as candidates for deletion after being merged or stale for ${days} days:\n\n"
for c in "${candidates[@]}"; do
	branch=${c%|*}
	reason=${c#*|}
	issue_body+="- [ ] ${branch} — ${reason}\n"
done

echo "Ensuring label 'branch-cleanup' exists"
if ! gh label list --limit 100 | grep -q "branch-cleanup"; then
	gh label create branch-cleanup --color FF0000 --description "Branches identified by automation for potential deletion" || true
fi
echo "Creating issue to review branch deletion"
issue_title="Branch cleanup candidates - ${repo} - $(date -u +%Y-%m-%d)"
created_issue=$(gh issue create --title "$issue_title" --body "$issue_body" --label "branch-cleanup" --assignee "@me" 2>/dev/null || true)
if [[ -n $created_issue ]]; then
	echo "Created issue: $created_issue"
else
	echo "Failed to create issue; creating a new issue via API fallback"
	echo "$issue_body" >/tmp/branch-cleanup.md
	gh issue create --title "$issue_title" --body-file /tmp/branch-cleanup.md --label branch-cleanup || true
fi

if [[ $auto_delete -eq 1 ]]; then
	echo "Auto-deleting branches (creating archival tags first)"
	for c in "${candidates[@]}"; do
		branch=${c%|*}
		echo "Archiving and deleting branch ${branch}"
		# Resolve latest commit SHA for branch
		commit_sha=$(gh api "/repos/${owner}/${repo}/git/refs/heads/${branch}" -q '.object.sha' 2>/dev/null || true)
		if [[ -z $commit_sha ]]; then
			echo "Could not determine SHA for ${branch}; skipping archival and deletion"
			continue
		fi
		tag_name="archive/${branch}-$(date -u +%Y%m%d%H%M%S)"
		echo "Creating tag ${tag_name} -> ${commit_sha}"
		# create annotated tag via git directly
		git fetch origin "${branch}" || true
		git tag -a "${tag_name}" "${commit_sha}" -m "Archive ${branch} before deletion"
		git push origin "refs/tags/${tag_name}" || echo "Failed to push tag ${tag_name}"
		echo "Deleting branch ${branch}"
		gh api -X DELETE "/repos/${owner}/${repo}/git/refs/heads/${branch}" || echo "Failed to delete branch ${branch}"
	done
fi

echo "Wrangle complete: searched ${days} day threshold and created issue with ${#candidates[@]} candidates"
exit 0
