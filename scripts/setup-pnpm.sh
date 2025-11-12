#!/usr/bin/env bash
set -euo pipefail

# Prepare pnpm on this machine via corepack and ensure a working pnpm install.
if ! command -v corepack >/dev/null 2>&1; then
	echo "corepack not available; skipping pnpm setup."
	exit 0
fi

echo "Enabling corepack and preparing pnpm..."
corepack enable
corepack prepare pnpm@latest --activate

echo "pnpm setup complete. Run 'pnpm install' to install packages."
