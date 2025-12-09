#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

if command -v corepack >/dev/null 2>&1; then
	corepack enable || true
	corepack prepare pnpm@10.23.0 --activate || true
fi

echo "[n00menon-verify] installing deps via workspace filter"
ALLOW_SUBREPO_PNPM_INSTALL=1 pnpm --filter n00menon install --frozen-lockfile || ALLOW_SUBREPO_PNPM_INSTALL=1 pnpm --filter n00menon install --no-frozen-lockfile

echo "[n00menon-verify] syncing docs"
pnpm --filter n00menon run docs:sync

echo "[n00menon-verify] running tests"
pnpm --filter n00menon test

echo "[n00menon-verify] building docs"
pnpm --filter n00menon run docs:build

echo "[n00menon-verify] done"
