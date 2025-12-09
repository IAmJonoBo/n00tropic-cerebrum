#!/usr/bin/env python3
"""Agent-grade wrapper around the workspace planning workflow."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
AGENT_CORE_SRC = ROOT / "n00t" / "packages" / "agent-core" / "src"
N00T_SRC = ROOT / "n00t"
DEFAULT_AGENTS_CONFIG = (
    ROOT / "n00t" / "packages" / "agent-core" / "config" / "agents.yaml"
)
for candidate in (AGENT_CORE_SRC, N00T_SRC):
    if candidate.exists():
        sys.path.insert(0, str(candidate))

try:  # noqa: WPS433 - runtime path injection for workspace scripts
    from agent_core.workflows.planning import WorkspacePlanningWorkflow  # type: ignore
except ImportError as exc:  # pragma: no cover - surfaced to operator
    raise RuntimeError(
        "agent_core.workflows is unavailable; ensure n00t packages are bootstrapped."
    ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brief", nargs="?", help="Path to the brief to plan")
    parser.add_argument(
        "--brief",
        dest="brief_override",
        help="Optional alternate brief input (path or inline text)",
    )
    parser.add_argument("--model", help="Preferred LLM identifier")
    parser.add_argument("--output", help="Override plan markdown output path")
    parser.add_argument("--telemetry", help="Override telemetry JSON path")
    parser.add_argument(
        "--airgapped", action="store_true", help="Force air-gapped provider selection"
    )
    parser.add_argument(
        "--force", action="store_true", help="Regenerate even when cached"
    )
    parser.add_argument(
        "--check-only",
        dest="check_only",
        action="store_true",
        help="Only validate; do not write plan files",
    )
    parser.add_argument(
        "--run-scripts",
        dest="run_scripts",
        action="store_true",
        help="Execute referenced scripts rather than dry-run",
    )
    parser.add_argument(
        "--yagni-threshold", type=float, help="Fail if YAGNI score exceeds this value"
    )
    parser.add_argument(
        "--conflict-limit", type=int, help="Fail if conflict count exceeds this limit"
    )
    parser.add_argument(
        "--agents-config",
        default=str(DEFAULT_AGENTS_CONFIG),
        help="Path to agent-core agents.yaml (exported in payload for sims)",
    )
    return parser


def _coerce_value(value: str) -> Any:
    stripped = value.strip()
    if not stripped:
        return ""
    if stripped[0] in "[{":
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return stripped
    lowered = stripped.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if "_" not in stripped:
            return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        return stripped


def _load_env_inputs() -> dict[str, Any]:
    inputs: dict[str, Any] = {}
    raw = os.environ.get("CAPABILITY_INPUTS")
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("CAPABILITY_INPUTS must be valid JSON") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("CAPABILITY_INPUTS must decode to an object")
        inputs.update(parsed)

    prefix = "INPUT_"
    for key, val in os.environ.items():
        if not key.startswith(prefix):
            continue
        normalized = key[len(prefix) :].lower()
        normalized = normalized.replace("__", "-").replace("-", "_")
        inputs.setdefault(normalized, _coerce_value(val))
    return inputs


def _extract_cli_overrides(
    args: argparse.Namespace, defaults: argparse.Namespace
) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    for key, value in vars(args).items():
        default_value = getattr(defaults, key, None)
        if value is None:
            continue
        if default_value is None and value is None:
            continue
        if value != default_value:
            overrides[key] = value
    return overrides


def _merge_inputs(*layers: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for layer in layers:
        if not layer:
            continue
        for key, value in layer.items():
            if value is None:
                continue
            merged[key] = value
    return merged


async def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    defaults = parser.parse_args([])

    env_inputs = _load_env_inputs()
    cli_overrides = _extract_cli_overrides(args, defaults)
    base_inputs = vars(defaults).copy()
    merged_inputs = _merge_inputs(base_inputs, env_inputs, cli_overrides)

    brief_value = merged_inputs.get("brief_override") or merged_inputs.get("brief")
    if not brief_value:
        raise SystemExit("A brief path or inline brief content is required")

    agents_config_path = Path(merged_inputs.get("agents_config", DEFAULT_AGENTS_CONFIG))
    agents_config: dict[str, Any] | None = None
    if agents_config_path.exists():
        try:
            agents_config = yaml.safe_load(
                agents_config_path.read_text(encoding="utf-8")
            )
        except Exception as exc:  # pragma: no cover - surfaced to operator
            print(
                f"[workspace-plan-workflow] Warning: failed to load agents config {agents_config_path}: {exc}",
                file=sys.stderr,
            )

    workflow = WorkspacePlanningWorkflow(repo_root=ROOT)
    result = await workflow.run(
        brief=brief_value,
        model=merged_inputs.get("model"),
        output=merged_inputs.get("output"),
        telemetry=merged_inputs.get("telemetry"),
        airgapped=merged_inputs.get("airgapped"),
        force=merged_inputs.get("force"),
        check_only=merged_inputs.get("check_only"),
        run_scripts=merged_inputs.get("run_scripts"),
        yagni_threshold=merged_inputs.get("yagni_threshold"),
        conflict_limit=merged_inputs.get("conflict_limit"),
    )

    payload: dict[str, Any] = {
        "status": result.outputs.get("status", result.status),
        "planPath": result.outputs.get("planPath"),
        "briefPath": result.outputs.get("briefPath"),
        "telemetryPath": result.outputs.get("telemetryPath"),
        "agentsConfigPath": str(agents_config_path),
        "agents": agents_config,
        "metrics": result.outputs.get("metrics", {}),
        "steps": [
            {
                "name": step.name,
                "status": step.status,
                "warnings": step.warnings,
                "durationMs": round(step.duration_ms, 2),
            }
            for step in result.steps
        ],
        "artifacts": result.artifacts,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(asyncio.run(main()))
