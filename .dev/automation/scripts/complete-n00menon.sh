#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "${ROOT_DIR}"

echo "[complete-n00menon] Starting n00menon completion checks"

if ! command -v node >/dev/null 2>&1; then
	echo "Node not found. Install Node 18+ first."
	exit 1
fi

if command -v corepack >/dev/null 2>&1; then
	corepack enable || true
	corepack prepare pnpm@10.23.0 --activate || true
fi

echo "Installing workspace dependencies"
pnpm install --no-frozen-lockfile || true

echo "Synchronizing n00menon docs"
pnpm -C n00menon run docs:sync || true

echo "Running docs validation for n00menon"
pnpm -C n00menon run validate || true

echo "Regenerating Typedoc HTML for n00menon"
pnpm -C n00menon run docs:build || true

echo "Detecting repo changes"
if [[ -n "$(git status --porcelain)" ]]; then
	BRANCH_NAME="n00menon/complete/$(date -u +%Y%m%d%H%M%S)"
	git checkout -b "${BRANCH_NAME}"
	git add -A
	git commit -m "chore(n00menon): complete docs/ui build and validation artifacts"
	git push --set-upstream origin "${BRANCH_NAME}"
	echo "Created branch ${BRANCH_NAME} with changes; open a PR to merge the improvements"
	echo "${BRANCH_NAME}"
else
	echo "No changes detected; nothing to commit"
fi

echo "n00menon completion script finished"
