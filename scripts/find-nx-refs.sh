#!/usr/bin/env bash
set -euo pipefail

echo "Searching for Nx references in the workspace..."

# Show files containing Nx references, excluding node_modules and build dirs
rg --hidden --line-number --no-ignore-vcs --glob '!node_modules' --glob '!**/dist/**' '(^|\W)nx(\W|$)|nx run |nx affected|nx run-many|nx graph|nx.json|@nx/' || true

echo "Done."
