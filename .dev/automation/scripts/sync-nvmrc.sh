#!/usr/bin/env bash
set -euo pipefail

# Keep subrepositories aligned with the workspace Node pin by linking their
# .nvmrc files back to the root .nvmrc. This means bumping the workspace pin
# (n00-cerebrum) automatically propagates everywhere without remembering each repo.
# Repos listed in OVERRIDES can carry an explicit .nvmrc if they intentionally lead.

ROOT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
WORKSPACE_NVMRC="${ROOT_DIR}/.nvmrc"
if [[ ! -f ${WORKSPACE_NVMRC} ]]; then
	echo "error: workspace .nvmrc not found at ${WORKSPACE_NVMRC}" >&2
	exit 1
fi

# Repositories that should link back to the workspace .nvmrc by default.
REPOS=(
	n00-cortex
	n00-frontiers
	n00t
	n00clear-fusion
	n00menon
	n00-school
	n00tropic_HQ
	n00tropic
	n00plicate
)
# Repositories allowed to lead (keep their own .nvmrc) unless forced.
OVERRIDES=(n00tropic n00plicate)

force_flag=0
while [[ $# -gt 0 ]]; do
	case "$1" in
	--force)
		force_flag=1
		shift
		;;
	--repo)
		REPOS=("$2")
		shift 2
		;;
	*)
		echo "unknown argument: $1" >&2
		exit 1
		;;
	esac
done

is_override() {
	local name="$1"
	for item in "${OVERRIDES[@]}"; do
		if [[ ${item} == "${name}" ]]; then
			return 0
		fi
	done
	return 1
}

for repo in "${REPOS[@]}"; do
	repo_path="${ROOT_DIR}/${repo}"
	if [[ ! -d ${repo_path} ]]; then
		echo "skip ${repo} (directory not found)"
		continue
	fi
	target="${repo_path}/.nvmrc"
	rel="../.nvmrc"

	if is_override "${repo}"; then
		if [[ ${force_flag} -eq 0 ]]; then
			echo "skip ${repo} (override repo retains its own .nvmrc)"
			continue
		fi
	fi

	ln -sfn "${rel}" "${target}"
	echo "linked ${target} -> ${rel}"

done
