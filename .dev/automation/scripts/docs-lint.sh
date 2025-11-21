#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"
echo "[docs-lint] Running Vale and Lychee across docs"
echo "[docs-lint] Running n00menon lint/spell checks (Vale + cspell)"
pnpm -C n00menon run lint:spell || true
echo "[docs-lint] Running workspace cspell across docs"
pnpm exec cspell --config ./cspell.json 'docs/**/*' || true
pnpm exec vale --minAlertLevel warning docs || true
pnpm exec lychee --config .lychee.toml 'docs/**/*.md' || true
echo "[docs-lint] Completed"
