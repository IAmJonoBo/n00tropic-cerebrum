#!/usr/bin/env bash
set -uo pipefail

# docs-agents-refresh.sh
# Validates presence of AGENTS.md files across workspace repos.
# Part of the docs.refresh capability.

# shellcheck source=./lib/log.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/log.sh"

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)

CHECK_ONLY=0
REPOS=()

while [[ $# -gt 0 ]]; do
	case $1 in
	--check)
		CHECK_ONLY=1
		;;
	--repos)
		IFS=',' read -ra REPOS <<<"$2"
		shift
		;;
	--help)
		cat <<'USAGE'
Usage: docs-agents-refresh.sh [--check] [--repos repo1,repo2,...]

Validates presence of AGENTS.md files across workspace repos.

Options:
  --check       Only check presence, exit non-zero if missing
  --repos       Comma-separated list of repos to check (default: all)

Exit codes:
  0  All repos have AGENTS.md
  1  One or more repos missing AGENTS.md
USAGE
		exit 0
		;;
	*)
		log_error "Unknown argument: $1"
		exit 2
		;;
	esac
	shift
done

# Default repos to check
if [[ ${#REPOS[@]} -eq 0 ]]; then
	REPOS=(
		"."
		"n00-cortex"
		"n00-frontiers"
		"n00t"
		"n00tropic"
		"n00-horizons"
		"n00-school"
		"n00clear-fusion"
		"n00menon"
		"n00plicate"
		"n00-dashboard"
		"n00HQ"
		"n00man"
	)
fi

MISSING=()
VALID=()
EXIT_CODE=0

log_info "Checking AGENTS.md presence in ${#REPOS[@]} repos..."

for repo in "${REPOS[@]}"; do
	repo_path="$ROOT/$repo"
	agents_file="$repo_path/AGENTS.md"

	if [[ ! -d $repo_path ]]; then
		log_warn "Repo not found: $repo"
		continue
	fi

	if [[ -f $agents_file ]]; then
		VALID+=("$repo")
		log_info "✅ $repo/AGENTS.md"
	else
		MISSING+=("$repo")
		log_warn "❌ $repo/AGENTS.md missing"
		EXIT_CODE=1
	fi
done

echo ""
log_info "Summary:"
log_info "  Valid: ${#VALID[@]}"
log_info "  Missing: ${#MISSING[@]}"

if [[ ${#MISSING[@]} -gt 0 ]]; then
	echo ""
	log_warn "Missing AGENTS.md in:"
	for repo in "${MISSING[@]}"; do
		echo "  - $repo"
	done
fi

# Output JSON for capability consumers
JSON_OUTPUT=$(
	cat <<EOF
{
  "status": "$([[ $EXIT_CODE -eq 0 ]] && echo "succeeded" || echo "failed")",
  "valid": $(printf '%s\n' "${VALID[@]}" | jq -R . | jq -s .),
  "missing": $(printf '%s\n' "${MISSING[@]}" | jq -R . | jq -s .)
}
EOF
)

if [[ -n ${DOCS_REFRESH_JSON-} ]]; then
	echo "$JSON_OUTPUT" >"$DOCS_REFRESH_JSON"
	log_info "Wrote JSON output to $DOCS_REFRESH_JSON"
fi

exit "$EXIT_CODE"
