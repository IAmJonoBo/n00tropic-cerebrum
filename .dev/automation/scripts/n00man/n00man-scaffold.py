#!/usr/bin/env python3
"""Expose the n00man Agent Foundry via automation/MCP runners."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import argparse
import asyncio
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[4]
N00MAN_ROOT = ROOT / "n00man"
DOCS_ROOT = N00MAN_ROOT / "docs"
REGISTRY_PATH = DOCS_ROOT / "agent-registry.json"

sys.path.insert(0, str(ROOT))

from n00man.core import AgentFoundryExecutor, AgentGovernanceError  # noqa: E402


def _load_json_source(value: str | None) -> Any:
    if not value:
        return None
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def _load_env_inputs() -> dict[str, Any]:
    inputs: dict[str, Any] = {}
    for key in ("CAPABILITY_INPUTS", "CAPABILITY_INPUT", "CAPABILITY_PAYLOAD"):
        raw = os.environ.get(key)
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:  # pragma: no cover - surfaced to operator
            raise SystemExit(f"Failed to parse {key}: {exc}") from exc
        if isinstance(parsed, dict):
            inputs.update(parsed)
    prefix = "INPUT_"
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        normalized = key[len(prefix) :].lower().replace("-", "_")
        inputs.setdefault(normalized, value)
    return inputs


def _merge_inputs(
    env_inputs: dict[str, Any], cli_inputs: dict[str, Any]
) -> dict[str, Any]:
    merged = dict(env_inputs)
    for key, value in cli_inputs.items():
        if value is None:
            continue
        merged[key] = value
    return merged


def _ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def build_payload(inputs: Dict[str, Any]) -> Dict[str, Any]:
    agent_id = inputs.get("agent_id") or inputs.get("name")
    if not agent_id:
        raise SystemExit("agent_id (or name) is required")
    role = inputs.get("role")
    description = inputs.get("description")
    if not role or not description:
        raise SystemExit("role and description are required")

    capabilities: list[dict[str, Any]] | None = None
    if "capabilities_path" in inputs:
        capabilities = _load_json_source(str(inputs["capabilities_path"]))
    elif "capabilities_json" in inputs:
        capabilities = _load_json_source(str(inputs["capabilities_json"]))
    else:
        raw_capabilities = inputs.get("capabilities")
        if isinstance(raw_capabilities, list):
            capabilities = raw_capabilities  # type: ignore[assignment]
    guardrails: list[Any] | None = None
    if "guardrails_path" in inputs:
        guardrails = _load_json_source(str(inputs["guardrails_path"]))
    elif "guardrails_json" in inputs:
        guardrails = _load_json_source(str(inputs["guardrails_json"]))
    else:
        raw_guardrails = inputs.get("guardrails") or inputs.get("guardrail")
        if isinstance(raw_guardrails, list):
            guardrails = raw_guardrails
        elif isinstance(raw_guardrails, str):
            guardrails = [raw_guardrails]

    metadata: dict[str, Any] | None = None
    if "metadata_path" in inputs:
        metadata = _load_json_source(str(inputs["metadata_path"]))
    elif isinstance(inputs.get("metadata"), dict):
        metadata = inputs["metadata"]

    tags_value = inputs.get("tags") or inputs.get("tag")
    tags = _ensure_list(tags_value)

    fallback_value = inputs.get("model_fallback") or inputs.get("model_fallbacks")
    fallbacks = [str(entry) for entry in _ensure_list(fallback_value)]

    model_config = {
        "provider": inputs.get("model_provider") or inputs.get("provider") or "openai",
        "model": inputs.get("model_name") or inputs.get("model") or "gpt-5.1-codex",
        "fallbacks": fallbacks or ["openai/gpt-5.1-codex-mini"],
    }

    payload: Dict[str, Any] = {
        "agent_id": str(agent_id),
        "name": str(inputs.get("name") or agent_id),
        "role": str(role),
        "description": str(description),
        "capabilities": capabilities,
        "guardrails": guardrails,
        "tags": [str(tag) for tag in tags if tag],
        "model_config": model_config,
        "owner": inputs.get("owner") or "platform-ops",
        "status": inputs.get("status") or "draft",
        "metadata": metadata or {},
    }
    return payload


async def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    executor = AgentFoundryExecutor(docs_root=DOCS_ROOT, registry_path=REGISTRY_PATH)
    result = await executor.execute(**payload)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-id")
    parser.add_argument("--name")
    parser.add_argument("--role")
    parser.add_argument("--description")
    parser.add_argument("--owner")
    parser.add_argument("--status")
    parser.add_argument("--tag", action="append", dest="tag")
    parser.add_argument("--guardrail", action="append", dest="guardrail")
    parser.add_argument("--capabilities-path")
    parser.add_argument("--capabilities-json")
    parser.add_argument("--guardrails-path")
    parser.add_argument("--guardrails-json")
    parser.add_argument("--metadata-path")
    parser.add_argument("--model-provider")
    parser.add_argument("--model-name")
    parser.add_argument("--model-fallback", action="append", dest="model_fallback")

    args = parser.parse_args()
    env_inputs = _load_env_inputs()
    cli_inputs = {key: value for key, value in vars(args).items()}
    merged_inputs = _merge_inputs(env_inputs, cli_inputs)

    try:
        payload = build_payload(merged_inputs)
        result = asyncio.run(run(payload))
    except AgentGovernanceError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}))
        return 2
    except Exception as exc:  # pragma: no cover - surfaced to operator
        print(json.dumps({"status": "failed", "error": str(exc)}))
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
