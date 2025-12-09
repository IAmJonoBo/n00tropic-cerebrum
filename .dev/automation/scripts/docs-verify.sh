#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"
echo "[docs-verify] Verifying n00menon layout"
pnpm -C n00menon run docs:verify
echo "[docs-verify] OK"
