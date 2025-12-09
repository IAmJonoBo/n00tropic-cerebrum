#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "${ROOT_DIR}"

REPORT_DIR="${ROOT_DIR}/artifacts/tmp/branch-wrangler"
TIMESTAMP="$(date -u +%Y%m%d%H%M%S)"
REPORT_FILE="${REPORT_DIR}/report-${TIMESTAMP}.md"

mkdir -p "${REPORT_DIR}"

command -v gh >/dev/null 2>&1 || {
	echo "GitHub CLI 'gh' is required" >&2
	exit 1
}
command -v jq >/dev/null 2>&1 || {
	echo "jq is required" >&2
	exit 1
}

mapfile -t REPOS < <(git config --file .gitmodules --get-regexp path 2>/dev/null | awk '{print $2}')
REPOS=("." "${REPOS[@]-}")

append_report_header() {
	cat <<EOF >>"${REPORT_FILE}"
# Branch wrangler report (${TIMESTAMP} UTC)

> Script: .dev/automation/scripts/tmp-branch-audit.sh
> Generated: $(date -u '+%Y-%m-%d %H:%M:%S UTC')

EOF
}

append_repo_section() {
	local repo_path="$1"
	local summary="$2"
	local conflicts="$3"
	printf '\n## %s\n\n' "${repo_path}" >>"${REPORT_FILE}"
	printf '| Branch | Committer | Commit Date (UTC) | Ahead | Behind | PR | Recommendation | Command |\n' >>"${REPORT_FILE}"
	printf '| --- | --- | --- | --- | --- | --- | --- | --- |\n' >>"${REPORT_FILE}"
	printf '%s' "${summary}" >>"${REPORT_FILE}"
	if [[ -n ${conflicts} ]]; then
		printf '\n**Unresolved merge markers (%s):**\n\n' "$(printf '%s' "${conflicts}" | sed '/^$/d' | wc -l | tr -d ' ')" >>"${REPORT_FILE}"
		printf '```\n%s\n```\n' "${conflicts}" >>"${REPORT_FILE}"
	fi
}

format_row() {
	local branch="$1" committer="$2" commit_date="$3" ahead="$4" behind="$5" pr_desc="$6" recommendation="$7" command="$8"
	printf '| `%s` | %s | %s | %s | %s | %s | %s | `%s` |\n' \
		"${branch}" "${committer}" "${commit_date}" "${ahead}" "${behind}" "${pr_desc}" "${recommendation}" "${command}"
}

classify_branch() {
	local ahead="$1" pr_state="$2" pr_url="$3"
	local recommendation="review"
	local reason="manual review required"

	if [[ ${pr_state} == "MERGED" ]]; then
		recommendation="delete"
		reason="PR merged"
	elif [[ ${pr_state} == "OPEN" ]]; then
		recommendation="keep"
		reason="PR open"
	elif [[ ${ahead} == "0" ]]; then
		recommendation="delete"
		reason="branch matches default"
	elif [[ -z ${pr_state} && ${ahead} =~ ^[0-9]+$ && ${ahead} -gt 0 ]]; then
		recommendation="review"
		reason="no PR"
	fi

	if [[ -n ${pr_url} && ${pr_state} != "" ]]; then
		reason+=" (${pr_state}: ${pr_url})"
	fi

	printf '%s' "${recommendation}|${reason}"
}

append_report_header

for repo_path in "${REPOS[@]}"; do
	rel_path="${repo_path}"
	abs_path="${ROOT_DIR}/${repo_path}"
	if [[ ! -d ${abs_path} ]]; then
		echo "[branch-wrangler] Skipping missing repo ${repo_path}" >&2
		continue
	fi

	pushd "${abs_path}" >/dev/null || continue
	if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
		echo "[branch-wrangler] ${repo_path} is not a git worktree, skipping" >&2
		popd >/dev/null
		continue
	fi

	git remote update --prune >/dev/null 2>&1 || true

	default_ref=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null || echo "refs/remotes/origin/main")
	default_branch="${default_ref##*/}"

	origin_url=$(git remote get-url origin)
	owner=$(echo "${origin_url}" | sed -E 's#.*github.com[:/]+([^/]+)/([^/]+).git#\1#')
	repo=$(echo "${origin_url}" | sed -E 's#.*github.com[:/]+([^/]+)/([^/]+).git#\2#')
	gh_repo="${owner}/${repo}"

	mapfile -t remote_branches < <(git for-each-ref --format '%(refname:short)' "refs/remotes/origin" | grep -v 'HEAD$' || true)
	repo_rows=""
	conflict_markers="$(git grep -n '^<<<<<<< ' -- ':!.git' || true)"

	for remote_branch in "${remote_branches[@]}"; do
		short_branch="${remote_branch#origin/}"
		if [[ ${short_branch} == "${default_branch}" || ${short_branch} == "origin" ]]; then
			continue
		fi

		commit_info=$(git log -1 --pretty='%cI|%cn' "${remote_branch}" 2>/dev/null || echo 'unknown|unknown')
		commit_date=${commit_info%%|*}
		committer=${commit_info#*|}

		ahead_behind=$(git rev-list --left-right --count "${remote_branch}...origin/${default_branch}" 2>/dev/null || echo '0 0')
		read -r behind ahead <<<"${ahead_behind}"

		pr_json=$(gh pr list --repo "${gh_repo}" --head "${short_branch}" --state all --limit 1 --json number,state,url 2>/dev/null || echo '[]')
		pr_desc="none"
		pr_state=""
		pr_url=""
		if jq -e 'length > 0' >/dev/null 2>&1 <<<"${pr_json}"; then
			pr_number=$(jq -r '.[0].number' <<<"${pr_json}")
			pr_state=$(jq -r '.[0].state' <<<"${pr_json}")
			pr_url=$(jq -r '.[0].url' <<<"${pr_json}")
			pr_desc="#${pr_number} (${pr_state})"
		fi

		classify_output=$(classify_branch "${ahead}" "${pr_state}" "${pr_url}")
		recommendation=${classify_output%%|*}
		reason=${classify_output#*|}
		command="git push origin --delete ${short_branch}"

		repo_rows+="$(format_row "${short_branch}" "${committer}" "${commit_date}" "${ahead}" "${behind}" "${pr_desc}" "${recommendation}" "${command}")\n"
		printf '[branch-wrangler] %s: %s (%s) -> %s\n' "${repo_path}" "${short_branch}" "${pr_desc}" "${recommendation}" >&2
		printf '    reason: %s\n' "${reason}" >&2
	done

	append_repo_section "${rel_path}" "${repo_rows}" "${conflict_markers}"
	popd >/dev/null
done

printf '\nReport written to %s\n' "${REPORT_FILE}"
