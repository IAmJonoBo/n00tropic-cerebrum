#!/usr/bin/env bash
set -euo pipefail

# Resets generated artefacts that frequently drift during local validation runs.
# Currently targets Next.js turbopack output committed under n00t/apps/control-centre.

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CLEANED=0

reset_next_turbo() {
	local repo="$ROOT_DIR/n00t"
	local rel_path="apps/control-centre/.next-turbo"
	if [[ ! -d $repo ]]; then
		return
	fi
	if [[ ! -d "$repo/$rel_path" ]]; then
		return
	fi
	if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
		return
	fi
	if git -C "$repo" diff --quiet -- "$rel_path"; then
		return
	fi
	echo "[cleanup] Resetting $rel_path in $(basename "$repo")"
	git -C "$repo" checkout -- "$rel_path"
	CLEANED=1
}

reset_next_turbo

if [[ $CLEANED -eq 0 ]]; then
	echo "[cleanup] No validation artefacts required resets"
else
	echo "[cleanup] Validation artefacts reset"
fi
