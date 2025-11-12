#!/usr/bin/env bash
set -euo pipefail

echo "Removing known Nx caches and artifacts..."

# Remove tmp nx-cache directories under the workspace
find . -type d -name 'nx-cache' -prune -exec rm -rf {} + || true
find . -type d -name '.nx' -prune -exec rm -rf {} + || true
# Remove specifically known paths
rm -rf n00plicate/tmp/nx-cache || true

# Helpful commands for users
echo "Running 'pnpm store prune' to ensure pnpm store cleanliness"
pnpm store prune || true

echo "Done. Check 'git status' for removed cache files; commit if appropriate."
