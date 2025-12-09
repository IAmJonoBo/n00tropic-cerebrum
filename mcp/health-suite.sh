#!/usr/bin/env bash
# Basic health check for the MCP suite.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$ROOT}"

PYTHON_BIN="python"
if [[ -x "${WORKSPACE_ROOT}/.venv/bin/python" ]]; then
	PYTHON_BIN="${WORKSPACE_ROOT}/.venv/bin/python"
elif command -v python >/dev/null 2>&1; then
	PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
	PYTHON_BIN="python3"
else
	echo "[mcp-health] python executable not found" >&2
	exit 1
fi

if ! command -v mcp-proxy >/dev/null 2>&1; then
	if ! "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1; then
import importlib.util, sys
sys.exit(0 if importlib.util.find_spec("mcp_proxy") else 1)
PY
		echo "[mcp-health] mcp-proxy not installed. Install with: pip install -e n00t/packages/mcp-proxy or pip install mcp-proxy" >&2
		exit 1
	fi
fi

export OTEL_TRACES_EXPORTER="${OTEL_TRACES_EXPORTER:-none}"
export OTEL_METRICS_EXPORTER="${OTEL_METRICS_EXPORTER:-none}"

MCP_PROXY_CMD=("mcp-proxy")
if ! command -v mcp-proxy >/dev/null 2>&1; then
	MCP_PROXY_CMD=("${PYTHON_BIN}" -m mcp_proxy.cli)
fi

set -x
env WORKSPACE_ROOT="$WORKSPACE_ROOT" "${MCP_PROXY_CMD[@]}" --config "${WORKSPACE_ROOT}/mcp/mcp-suite.yaml" list

VALIDATOR_PY="${WORKSPACE_ROOT}/.venv/bin/python"
if [[ ! -x ${VALIDATOR_PY} ]]; then
	VALIDATOR_PY="${PYTHON_BIN}"
fi

VALIDATION_FLAGS=("--federation" "${WORKSPACE_ROOT}/mcp/federation_manifest.json")
if [[ ${RUN_MODULE_HEALTH:-0} == "1" ]]; then
	VALIDATION_FLAGS+=("--run-health")
fi

"${VALIDATOR_PY}" "${WORKSPACE_ROOT}/mcp/validate_manifest.py" "${VALIDATION_FLAGS[@]}"

DISCOVERY_SCRIPT="${WORKSPACE_ROOT}/mcp/discover_capability_candidates.py"
DISCOVERY_BASELINE="${WORKSPACE_ROOT}/mcp/capability_candidates.baseline.json"
if [[ -f ${DISCOVERY_SCRIPT} ]]; then
	DISCOVERY_ARGS=("${DISCOVERY_SCRIPT}" "--format" "table")
	if [[ -f ${DISCOVERY_BASELINE} ]]; then
		DISCOVERY_ARGS+=("--baseline" "${DISCOVERY_BASELINE}" "--fail-on-new")
	fi
	"${VALIDATOR_PY}" "${DISCOVERY_ARGS[@]}"
fi

# Full tool fetch can be slow if servers emit telemetry; enable with RUN_TOOLS=1
if [[ ${RUN_TOOLS:-0} == "1" ]]; then
	env WORKSPACE_ROOT="$WORKSPACE_ROOT" "${MCP_PROXY_CMD[@]}" --config "${WORKSPACE_ROOT}/mcp/mcp-suite.yaml" tools
fi
