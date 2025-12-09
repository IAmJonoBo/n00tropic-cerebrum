#!/usr/bin/env bash
set -euo pipefail

echo "Centralizing pnpm store and hoisting workspace dependencies"

if ! command -v pnpm &>/dev/null; then
	echo "pnpm not found, try: corepack enable && corepack prepare pnpm@10.23.0 --activate"
	exit 1
fi

echo "Stashing local changes to prevent accidental loss"
git stash -u -q || true

echo "Cleaning nested node_modules to reclaim space..."
find . -name node_modules -type d -prune -exec rm -rf '{}' + || true

echo "Ensuring pnpm workspace install is hoisted to root"
pnpm -w install

echo "Pruning pnpm store of unused packages"
pnpm store prune

echo "Done. If you need to restore your stash, run: git stash pop"
