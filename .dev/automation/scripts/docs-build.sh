#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"
echo "[docs-build] Running Antora CI playbook"
pnpm exec antora antora-playbook.ci.yml --stacktrace
echo "[docs-build] Completed"
