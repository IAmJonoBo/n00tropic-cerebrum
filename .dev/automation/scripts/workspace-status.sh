#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

printf "[workspace-status] Root repo: %s\n" "$ROOT_DIR"

git status --short --branch

if [ -f .gitmodules ]; then
  echo
  echo "[workspace-status] Submodule summary:" 
  git submodule status || true
fi

if command -v trunk >/dev/null 2>&1; then
  echo
  echo "[workspace-status] Trunk status (root):"
  trunk status || true
else
  echo
  echo "[workspace-status] Trunk not found on PATH; skipping trunk status."
fi
