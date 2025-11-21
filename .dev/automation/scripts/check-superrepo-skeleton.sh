#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../../.." && pwd)
CHECK_SCRIPT="${SCRIPT_DIR}/check-workspace-skeleton.py"

if [[ ! -f $CHECK_SCRIPT ]]; then
	echo "Missing workspace skeleton checker at $CHECK_SCRIPT" >&2
	exit 1
fi

python3 "$CHECK_SCRIPT" "$@"

# Keep repo context fresh for agents and doctors.
python3 "${ROOT_DIR}/cli.py" repo-context >/dev/null
