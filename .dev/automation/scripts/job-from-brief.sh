#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

if [[ $# -lt 1 ]]; then
  echo "Usage: $(basename "$0") --from <brief-path> [--owner ...] [--title ...] [--tags ...]" >&2
  exit 1
fi

python3 "$SCRIPT_DIR/project-orchestration.py" record-job "$@"
