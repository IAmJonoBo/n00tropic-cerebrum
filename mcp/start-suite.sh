#!/usr/bin/env bash
# Start the full MCP suite: docs server + capability shim + mcp-proxy serve.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$ROOT}"
export WORKSPACE_ROOT
ARTIFACTS="${WORKSPACE_ROOT}/artifacts/mcp"
mkdir -p "$ARTIFACTS"

log() {
	printf '[mcp-suite] %s\n' "$*"
}

# Prefer repo venv if present (activate even if not executable)
if [[ -f "${WORKSPACE_ROOT}/.venv/bin/activate" ]]; then
	# shellcheck source=/dev/null
	source "${WORKSPACE_ROOT}/.venv/bin/activate"
fi

PYTHON_BIN="python"
if [[ -x "${WORKSPACE_ROOT}/.venv/bin/python" ]]; then
	PYTHON_BIN="${WORKSPACE_ROOT}/.venv/bin/python"
elif command -v python >/dev/null 2>&1; then
	PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
	PYTHON_BIN="python3"
else
	log "python interpreter not found"
	exit 1
fi
command -v "${PYTHON_BIN}" >/dev/null 2>&1 || {
	log "python interpreter '${PYTHON_BIN}' not executable"
	exit 1
}

# Default tracing to noop unless explicitly set
export OTEL_TRACES_EXPORTER="${OTEL_TRACES_EXPORTER:-none}"
export OTEL_METRICS_EXPORTER="${OTEL_METRICS_EXPORTER:-none}"

MCP_PROXY_CMD=()

ensure_mcp_proxy() {
	if command -v mcp-proxy >/dev/null 2>&1; then
		MCP_PROXY_CMD=("mcp-proxy")
		return 0
	fi
	if "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1; then
import importlib.util, sys
sys.exit(0 if importlib.util.find_spec("mcp_proxy") else 1)
PY
		MCP_PROXY_CMD=("${PYTHON_BIN}" -m mcp_proxy.cli)
		return 0
	fi
	log "mcp-proxy not installed. Install with: pip install -e n00t/packages/mcp-proxy or pip install mcp-proxy"
	exit 1
}

start_bg() {
	local name="$1"
	shift
	local log_file="${ARTIFACTS}/${name}.log"
	log "starting ${name} -> ${log_file}"
	("$@") >"$log_file" 2>&1 &
	echo $! >"${ARTIFACTS}/${name}.pid"
}

# Start docs + capabilities shim in background
start_bg docs "${PYTHON_BIN}" "${WORKSPACE_ROOT}/mcp/docs_server/server.py"
start_bg capabilities "${PYTHON_BIN}" "${WORKSPACE_ROOT}/mcp/capabilities_server.py"

# Start proxy in foreground (use exec to forward signals)
ensure_mcp_proxy
PORT="${MCP_PROXY_PORT:-8080}"
log "starting mcp-proxy on port ${PORT}"
exec "${MCP_PROXY_CMD[@]}" --config "${WORKSPACE_ROOT}/mcp/mcp-suite.yaml" serve --port "${PORT}"
