#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="$ROOT_DIR/automation/workspace.manifest.json"

if [[ ! -f $MANIFEST ]]; then
	echo "[tag-propagate] manifest missing: $MANIFEST" >&2
	exit 1
fi

paths=($(jq -r '.repos[].path' "$MANIFEST"))
for p in "${paths[@]}"; do
	repo_path="$ROOT_DIR/$p"
	if [[ ! -d $repo_path ]]; then
		echo "[tag-propagate] skip missing repo $repo_path" >&2
		continue
	fi
	if [[ ! -d "$repo_path/docs" ]]; then
		echo "[tag-propagate] skip $repo_path (no docs dir)" >&2
		continue
	fi
	echo "[tag-propagate] enforcing tags in $repo_path/docs" >&2
	node "$ROOT_DIR/scripts/enforce-doc-tags.mjs" --root "$repo_path"
done

echo "[tag-propagate] done" >&2
