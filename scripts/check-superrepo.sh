#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
REQUIRED_REPOS=(
	"n00-frontiers"
	"n00-cortex"
	"n00-horizons"
	"n00-school"
	"n00t"
	"n00plicate"
	"n00tropic"
	"n00clear-fusion"
)

missing=()
for repo in "${REQUIRED_REPOS[@]}"; do
	if [[ ! -d "$ROOT_DIR/$repo/.git" && ! -f "$ROOT_DIR/$repo/.git" ]]; then
		missing+=("$repo")
	fi
done

if [[ ${#missing[@]} -gt 0 ]]; then
	echo "[superrepo-check] Missing expected subrepositories: ${missing[*]}" >&2
	echo "Run 'git submodule update --init --recursive' from $ROOT_DIR" >&2
	exit 1
fi

pushd "$ROOT_DIR" >/dev/null
if ! git submodule status >/dev/null 2>&1; then
	echo "[superrepo-check] git submodule status failed" >&2
	exit 1
fi

git submodule status
popd >/dev/null

echo "[superrepo-check] Validating workspace skeleton (cli/env/tests/automation)"
python3 "$ROOT_DIR/.dev/automation/scripts/check-workspace-skeleton.py"

echo "[superrepo-check] All required subrepos present."
