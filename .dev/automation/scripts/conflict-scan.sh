#!/usr/bin/env bash
set -euo pipefail

# Optional: write a markdown report when invoked with --report <path>
REPORT_FILE=""
if [[ ${1-} == "--report" ]]; then
	shift
	REPORT_FILE="${1-}"
	if [[ -z ${REPORT_FILE} ]]; then
		echo "Usage: $0 [--report <path>]" >&2
		exit 1
	fi
	shift || true
fi

# Scan the workspace (root + submodules) for unresolved git conflict markers.
# Exits non-zero if any are found.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "${ROOT_DIR}"

mapfile -t REPOS < <(git config --file .gitmodules --get-regexp path 2>/dev/null | awk '{print $2}')
REPOS=("." "${REPOS[@]-}")

overall_conflicts=0
report_body=""

scan_repo() {
	local repo_path="$1"
	local abs_path="${ROOT_DIR}/${repo_path}"

	if [[ ! -d ${abs_path} ]]; then
		echo "[conflict-scan] Skipping missing repo ${repo_path}" >&2
		return
	fi

	pushd "${abs_path}" >/dev/null || return
	if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
		echo "[conflict-scan] ${repo_path} is not a git worktree, skipping" >&2
		popd >/dev/null
		return
	fi

	conflicts=$(git grep -n "^<<<<<<< " -- ':!.git' || true)
	if [[ -n ${conflicts} ]]; then
		count=$(printf '%s\n' "${conflicts}" | sed '/^$/d' | wc -l | tr -d ' ')
		overall_conflicts=$((overall_conflicts + count))
		echo
		echo "=== ${repo_path} (${count} markers) ==="
		printf '%s\n' "${conflicts}"

		if [[ -n ${REPORT_FILE} ]]; then
			report_body+=$'\n'"## ${repo_path} (${count} markers)"$'\n\n'
			report_body+="\`\`\`\n${conflicts}\n\`\`\`\n"
		fi
	fi

	popd >/dev/null
}

for repo_path in "${REPOS[@]}"; do
	scan_repo "${repo_path}"
done

if [[ ${overall_conflicts} -gt 0 ]]; then
	if [[ -n ${REPORT_FILE} ]]; then
		mkdir -p "$(dirname "${REPORT_FILE}")"
		{
			printf '# Conflict Scan Report (%s UTC)\n\n' "$(date -u '+%Y-%m-%d %H:%M:%S')"
			printf 'Found **%s** unresolved merge markers.\n' "${overall_conflicts}"
			printf '%s\n' "${report_body}"
		} >"${REPORT_FILE}"
		echo "[conflict-scan] Wrote report to ${REPORT_FILE}"
	fi
	echo
	echo "[conflict-scan] Found ${overall_conflicts} unresolved merge markers."
	exit 1
else
	if [[ -n ${REPORT_FILE} ]]; then
		mkdir -p "$(dirname "${REPORT_FILE}")"
		printf '# Conflict Scan Report (%s UTC)\n\nNo unresolved merge markers detected.\n' "$(date -u '+%Y-%m-%d %H:%M:%S')" >"${REPORT_FILE}"
		echo "[conflict-scan] Wrote report to ${REPORT_FILE}"
	fi
	echo "[conflict-scan] No unresolved merge markers detected."
fi
