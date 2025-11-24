#!/usr/bin/env bash
# Synchronise n00-cortex with exports from n00-frontiers.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
CORTEX_DIR="$ROOT/n00-cortex"

MODE="run"
if [[ ${1-} == "--check" ]]; then
	MODE="check"
	shift
fi

# Allow capability runners to supply JSON payload via environment.
if [[ $MODE == "run" ]]; then
	if python3 - <<'PY' >/dev/null 2>&1; then
import json
import os
import sys

payload = os.environ.get("CAPABILITY_PAYLOAD") or os.environ.get("CAPABILITY_INPUT")
if not payload:
    raise SystemExit(1)
try:
    data = json.loads(payload)
except json.JSONDecodeError:
    raise SystemExit(1)

raise SystemExit(0 if data.get("check") else 1)
PY
		MODE="check"
	fi
fi

if [[ ! -d "$CORTEX_DIR/node_modules" ]]; then
	(cd "$CORTEX_DIR" && npm install --silent --no-progress)
fi

pushd "$CORTEX_DIR" >/dev/null
if [[ $MODE == "check" ]]; then
	npm run ingest:frontiers:check --silent
else
	npm run ingest:frontiers --silent
fi
popd >/dev/null
