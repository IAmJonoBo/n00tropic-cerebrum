#!/usr/bin/env bash
set -euo pipefail

# Prepare pnpm on this machine via corepack, with an npm fallback for runners
# that lack the corepack shim.
PNPM_VERSION=${PNPM_VERSION:-10.23.0}

if command -v corepack >/dev/null 2>&1; then
	echo "Enabling corepack and preparing pnpm@${PNPM_VERSION}..."
	corepack enable
	corepack prepare "pnpm@${PNPM_VERSION}" --activate
	echo "pnpm setup complete via corepack."
elif command -v npm >/dev/null 2>&1; then
	echo "corepack not available; installing pnpm@${PNPM_VERSION} globally via npm..."
	npm install -g "pnpm@${PNPM_VERSION}"
	echo "pnpm setup complete via npm global install."
else
	echo "Neither corepack nor npm is available; cannot install pnpm."
	exit 1
fi

echo "Run 'pnpm install' at the workspace root to hydrate dependencies."
