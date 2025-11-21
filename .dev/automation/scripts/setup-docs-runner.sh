#!/usr/bin/env bash
set -euo pipefail

# Install/prereq script for provisioning a machine to run Antora docs builds
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

echo "[setup-docs-runner] Root: ${ROOT_DIR}"

if ! command -v node >/dev/null 2>&1; then
	echo "Node.js not found. Please install Node 18+ (or 20/24) first."
	exit 1
fi

echo "Ensuring corepack/pnpm are available"
if command -v corepack >/dev/null 2>&1; then
	corepack enable || true
	corepack prepare pnpm@10.22.0 --activate || true
else
	echo "corepack not available; installing pnpm fallback"
	npm i -g pnpm@10.22.0
fi

echo "Installing Antora CLI and site generator locally"
pnpm add -w --dev @antora/cli@3.1.14 @antora/site-generator@3.1.14 @antora/lunr-extension@1.0.0-alpha.12 || true

echo "Installing Vale and Lychee (linting tools)"
if command -v apt-get >/dev/null 2>&1; then
	sudo apt-get update
	sudo apt-get install -y jq ripgrep
fi

# Vale is a release binary; if available via package, prefer package manager, else fallback to npm 'vale' wrapper
if ! command -v vale >/dev/null 2>&1; then
	if command -v apt-get >/dev/null 2>&1; then
		sudo apt-get install -y vale || true
	else
		pnpm add -w --dev vale || true
	fi
fi

if ! command -v lychee >/dev/null 2>&1; then
	pnpm add -w --dev lycheeverse/lychee-action@v2 || true
fi

echo "Installing cspell (spell check)"
if ! command -v cspell >/dev/null 2>&1; then
	pnpm add -w --dev cspell || true
fi

echo "Installing Antora theme generator helpers and dependencies"
pnpm install --frozen-lockfile || true

echo "Docs runner setup complete. Verify with: pnpm exec antora --version && vale --version"
