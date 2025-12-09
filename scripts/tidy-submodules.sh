#!/usr/bin/env bash
set -euo pipefail

# One-shot helper to keep submodules synced and manifest-compliant.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[tidy] syncing submodule remotes" >&2
git -C "$ROOT_DIR" submodule sync --recursive

echo "[tidy] updating submodules" >&2
git -C "$ROOT_DIR" submodule update --init --recursive || true

echo "[tidy] running manifest gate" >&2
if ! bash "$ROOT_DIR/.dev/automation/scripts/manifest-gate.sh"; then
	echo "[tidy] manifest gate failed; add missing repos to automation/workspace.manifest.json" >&2
	exit 1
fi

echo "[tidy] running skeleton check (apply stubs + hooks)" >&2
python3 "$ROOT_DIR/.dev/automation/scripts/check-workspace-skeleton.py" --apply || true

echo "[tidy] enforcing doc tags across repos" >&2
bash "$ROOT_DIR/scripts/tag-propagate.sh"

echo "[tidy] done" >&2
