#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
STACK_SCRIPT="${SCRIPT_DIR}/erpnext-stack.sh"

if [[ ! -x ${STACK_SCRIPT} ]]; then
	echo "erpnext-stack.sh not found or not executable at ${STACK_SCRIPT}" >&2
	exit 1
fi

exec "${STACK_SCRIPT}" run "$@"
