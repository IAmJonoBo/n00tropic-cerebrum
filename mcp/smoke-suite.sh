#!/usr/bin/env bash
# Lightweight MCP suite smoke tests (no long-running workloads).
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$ROOT}"

if [[ -x "${WORKSPACE_ROOT}/.venv/bin/activate" ]]; then
	# shellcheck source=/dev/null
	source "${WORKSPACE_ROOT}/.venv/bin/activate"
fi

export OTEL_TRACES_EXPORTER="${OTEL_TRACES_EXPORTER:-none}"
export OTEL_METRICS_EXPORTER="${OTEL_METRICS_EXPORTER:-none}"

PYTHON_BIN="python"
if [[ -x "${WORKSPACE_ROOT}/.venv/bin/python" ]]; then
	PYTHON_BIN="${WORKSPACE_ROOT}/.venv/bin/python"
elif command -v python >/dev/null 2>&1; then
	PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
	PYTHON_BIN="python3"
else
	echo "[smoke] python executable not found" >&2
	exit 1
fi

echo "[smoke] verifying capability shim loadable"
"${PYTHON_BIN}" "${WORKSPACE_ROOT}/mcp/capabilities_server.py" --list | head -n 5

echo "[smoke] mcp-proxy list (parses suite config)"
MCP_PROXY_CMD=("mcp-proxy")
if ! command -v mcp-proxy >/dev/null 2>&1; then
	MCP_PROXY_CMD=("${PYTHON_BIN}" -m mcp_proxy.cli)
fi
env WORKSPACE_ROOT="$WORKSPACE_ROOT" "${MCP_PROXY_CMD[@]}" --config "${WORKSPACE_ROOT}/mcp/mcp-suite.yaml" list

echo "[smoke] docs server page fetch (index) via local import"
"${PYTHON_BIN}" - <<'PY'
import asyncio, importlib.util, os
from pathlib import Path

root = Path(os.environ["WORKSPACE_ROOT"])
server_path = root / "mcp" / "docs_server" / "server.py"
spec = importlib.util.spec_from_file_location("docs_server", server_path)
docs = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(docs)  # type: ignore

async def main():
    page = docs.get_page("index")
    assert "content" in page, "docs.get_page missing content"
    print("[smoke] docs index length:", len(page.get("content", "")))

asyncio.run(main())
PY

echo "[smoke] capability shim sample call (noop: list only)"
"${PYTHON_BIN}" - <<'PY'
import os, sys
from pathlib import Path
root = Path(os.environ["WORKSPACE_ROOT"])
sys.path.insert(0, str(root))
import mcp as mcp_package
local_pkg = root / "mcp"
if str(local_pkg) not in mcp_package.__path__:
    mcp_package.__path__.append(str(local_pkg))
from mcp.capabilities_server import list_capabilities  # type: ignore
from mcp.federation_manifest import FederationManifest
from mcp.capabilities_manifest import CapabilityManifest

print("[smoke] capabilities count:", len(list_capabilities()))

fed_manifest = FederationManifest.load(root / "mcp" / "federation_manifest.json", root)
validated = 0
for module in fed_manifest.modules:
    manifest_path = module.manifest_path(root)
    repo_path = module.repo_path(root)
    manifest = CapabilityManifest.load(manifest_path, repo_path)
    enabled_caps = list(manifest.enabled_capabilities())
    for cap in enabled_caps:
        cap.resolved_entrypoint(repo_path, manifest_path.parent)
    print(f"[smoke] module {module.id}: {len(enabled_caps)} enabled capabilities")
    validated += len(enabled_caps)

print("[smoke] validated entrypoints:", validated)
PY

if [[ ${RUN_CAP_SMOKE:-0} == "1" ]]; then
	echo "[smoke] capability dry-run: deps.drift (format=json, dry-run mode)"
	TRUNK_CHECK_SCOPE=changed \
		"${WORKSPACE_ROOT}/.venv/bin/python" "${WORKSPACE_ROOT}/.dev/automation/scripts/deps-drift.py" --format json >/dev/null
fi

if [[ ${RUN_AI_WORKFLOW_PING:-0} == "1" ]]; then
	echo "[smoke] ai-workflow MCP ping (tool list)"
	env WORKSPACE_ROOT="$WORKSPACE_ROOT" mcp-proxy --config "${WORKSPACE_ROOT}/mcp/mcp-suite.yaml" tools | grep -i "ai-workflow" || true
fi

if [[ ${RUN_CORTEX_PING:-0} == "1" ]]; then
	echo "[smoke] cortex-catalog MCP ping (tool list)"
	env WORKSPACE_ROOT="$WORKSPACE_ROOT" mcp-proxy --config "${WORKSPACE_ROOT}/mcp/mcp-suite.yaml" tools | grep -i "cortex" || true
fi

echo "[smoke] done"
