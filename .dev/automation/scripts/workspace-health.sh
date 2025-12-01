#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'
# shellcheck source=./lib/log.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/log.sh"
# shellcheck source=../toolchain.env
source "$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)/toolchain.env"
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../../.." && pwd)

record_envelope() {
	local status="$1"
	local notes="$2"
	python3 "$SCRIPT_DIR/record-run-envelope.py" \
		--capability workspace.health \
		--status "$status" \
		--asset ".dev/automation/artifacts/workspace-health.json" \
		--notes "$notes" || true
}

finish() {
	local rc=$?
	if [[ $rc -eq 0 ]]; then
		record_envelope "success" "workspace-health succeeded"
	else
		record_envelope "failure" "workspace-health failed rc=$rc"
	fi
}
trap finish EXIT

python3 "$SCRIPT_DIR/workspace-health.py" "$@"
