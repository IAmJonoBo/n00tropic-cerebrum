#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)

MAX_DAYS=${TYPESENSE_MAX_AGE_DAYS:-${1:-7}}
export TYPESENSE_MAX_AGE_DAYS="$MAX_DAYS"

# Ensure pinned Node version
# shellcheck source=/dev/null
source "$ROOT/scripts/ensure-nvm-node.sh" 2>/dev/null || true

node "$ROOT/scripts/check-typesense-freshness.mjs"
printf '{"status":"ok","max_days":%s}\n' "$MAX_DAYS"
