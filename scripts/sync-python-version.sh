#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
PY_VERSION_FILE="$ROOT_DIR/.python-version"
if [[ ! -f $PY_VERSION_FILE ]]; then
	echo "workspace .python-version missing at $PY_VERSION_FILE" >&2
	exit 1
fi
REPOS=(
	n00-frontiers
	n00-cortex
	n00clear-fusion
	n00-school
	n00-horizons
	n00tropic
	n00t
)
for repo in "${REPOS[@]}"; do
	target="$ROOT_DIR/$repo/.python-version"
	if [[ -d $ROOT_DIR/$repo ]]; then
		ln -sfn ../.python-version "$target"
		echo "linked $target -> ../.python-version"
	else
		echo "skip $repo (missing dir)"
	fi
done
