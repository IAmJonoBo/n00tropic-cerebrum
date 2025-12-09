#!/usr/bin/env bash
# Run trunk check for MCP/CLI consumption. AGENT_HOOK: dependency-management
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
ARTIFACT_DIR="${ROOT_DIR}/artifacts/trunk"
mkdir -p "${ARTIFACT_DIR}"

if ! command -v trunk >/dev/null 2>&1; then
	echo "[trunk-lint] trunk CLI not found; install via trunk.io or run trunk-lint-setup.sh" >&2
	exit 1
fi

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SCOPE_FLAG=""
SCOPE_LABEL="full"
if [[ ${TRUNK_CHECK_SCOPE:-changed} == "changed" ]]; then
	SCOPE_FLAG="--changed"
	SCOPE_LABEL="changed"
fi

LOG_FILE="${ARTIFACT_DIR}/trunk-check-${SCOPE_LABEL}-${TIMESTAMP}.log"
FILTER_FLAG=()
if [[ -n ${TRUNK_CHECK_FILTER-} ]]; then
	FILTER_FLAG=(--filter "${TRUNK_CHECK_FILTER}")
fi

set +e
TRUNK_NO_PROGRESS=1 TRUNK_DISABLE_TELEMETRY=1 TRUNK_NONINTERACTIVE=1 \
	trunk check --no-fix ${SCOPE_FLAG} ${FILTER_FLAG[@]-} | tee "$LOG_FILE"
status=$?
set -e

echo "[trunk-lint] log=${LOG_FILE} status=${status}"
if [[ $status -ne 0 ]]; then
	exit $status
fi
exit 0
