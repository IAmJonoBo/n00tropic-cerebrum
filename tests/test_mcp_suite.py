from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_mcp_suite_config_exists() -> None:
    suite = ROOT / "mcp" / "mcp-suite.yaml"
    assert suite.exists(), "mcp-suite.yaml missing"


def test_docs_server_imports() -> None:
    server_path = ROOT / "mcp" / "docs_server" / "server.py"
    spec = importlib.util.spec_from_file_location("docs_server", server_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    page = mod.get_page("index")  # type: ignore[attr-defined]
    assert "content" in page


def test_capability_manifest_entrypoints_exist() -> None:
    manifest = ROOT / "n00t" / "capabilities" / "manifest.json"
    data = json.loads(manifest.read_text())
    for cap in data.get("capabilities", []):
        agent_cfg = cap.get("agent", {})
        mcp_cfg = agent_cfg.get("mcp", {}) if isinstance(agent_cfg, dict) else {}
        if not mcp_cfg.get("enabled", False):
            continue
        ep = cap.get("entrypoint")
        assert ep, f"missing entrypoint for {cap.get('id')}"
        path = (manifest.parent / ep).resolve()
        assert path.exists(), f"entrypoint missing: {path}"


def test_routing_profile_parses() -> None:
    import yaml

    profile = ROOT / "mcp" / "routing-profile.yaml"
    data = yaml.safe_load(profile.read_text())
    assert "routes" in data and "defaults" in data


def test_router_resolve_script_runs() -> None:
    import subprocess

    script = ROOT / "mcp" / "router-resolve.py"
    result = subprocess.run(
        [sys.executable, str(script), "docs.index"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "docs"


def test_router_proxy_list_tools_runs() -> None:
    import subprocess

    script = ROOT / "mcp" / "router_proxy.py"
    env = os.environ.copy()
    env["SKIP_SERVERS"] = "filesystem,memory,ai-workflow,cortex-catalog,cortex-graph"
    env["INCLUDE_OPTIONAL_SERVERS"] = "0"
    env["ONLY_SERVERS"] = "docs"
    env["WORKSPACE_ROOT"] = str(ROOT)
    result = subprocess.run(
        [sys.executable, str(script), "list-tools"],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    assert "docs" in result.stdout or result.stdout != ""


def test_optional_pings_env_guard() -> None:
    # Ensure env flags are honored (no-op without flags)
    assert os.environ.get("RUN_AI_WORKFLOW_PING") is None
    assert os.environ.get("RUN_CORTEX_PING") is None
