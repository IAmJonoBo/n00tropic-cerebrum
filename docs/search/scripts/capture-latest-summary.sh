#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
LOG_DIR="$ROOT_DIR/docs/search/logs"
SCRIPT="$ROOT_DIR/docs/search/scripts/save-typesense-summary.mjs"

if [[ ! -d $LOG_DIR ]]; then
	echo "Typesense log directory not found: $LOG_DIR" >&2
	exit 1
fi
latest=$(ls -1t "$LOG_DIR"/typesense-reindex-*.log 2>/dev/null | head -n 1 || true)
if [[ -z $latest ]]; then
	echo "No typesense-reindex logs found in $LOG_DIR" >&2
	exit 1
fi

node "$SCRIPT" "$latest"
echo "Generated summary for $(basename "$latest")"
