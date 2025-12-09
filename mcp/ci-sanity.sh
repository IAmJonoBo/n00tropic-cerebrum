#!/usr/bin/env bash
# CI sanity: health + smoke for MCP suite (no long-running lint/build).
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$ROOT}"

if [[ -x "${WORKSPACE_ROOT}/.venv/bin/activate" ]]; then
	# shellcheck source=/dev/null
	source "${WORKSPACE_ROOT}/.venv/bin/activate"
fi

export OTEL_TRACES_EXPORTER="${OTEL_TRACES_EXPORTER:-none}"
export OTEL_METRICS_EXPORTER="${OTEL_METRICS_EXPORTER:-none}"

WORKSPACE_ROOT="$WORKSPACE_ROOT" RUN_TOOLS=1 "${WORKSPACE_ROOT}/mcp/health-suite.sh"
WORKSPACE_ROOT="$WORKSPACE_ROOT" "${WORKSPACE_ROOT}/mcp/smoke-suite.sh"
