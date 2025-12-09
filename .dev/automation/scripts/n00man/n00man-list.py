#!/usr/bin/env python3
"""List n00man agent registry entries for automation surfaces."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

ROOT = Path(__file__).resolve().parents[4]
N00MAN_ROOT = ROOT / "n00man"
DOCS_ROOT = N00MAN_ROOT / "docs"
DEFAULT_REGISTRY = DOCS_ROOT / "agent-registry.json"

sys.path.insert(0, str(ROOT))

from n00man.core import AgentRegistry  # noqa: E402

if TYPE_CHECKING:  # pragma: no cover
    from n00man.core import AgentProfile


def _load_env_inputs() -> dict[str, Any]:
    inputs: dict[str, Any] = {}
    for key in ("CAPABILITY_INPUTS", "CAPABILITY_INPUT", "CAPABILITY_PAYLOAD"):
        raw = os.environ.get(key)
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:  # pragma: no cover
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


def _get_first(inputs: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key not in inputs:
            continue
        value = inputs[key]
        if value is None:
            continue
        return value
    return None


def _serialise_agent(profile: "AgentProfile") -> dict[str, Any]:
    payload = profile.to_dict()
    payload["agentId"] = payload.pop("agent_id")
    return payload


def _filter_agents(
    registry: AgentRegistry, filters: dict[str, Any]
) -> list[dict[str, Any]]:
    agents: list[AgentProfile] = registry.list()
    agent_id = _get_first(filters, "agent_id", "agentId", "name")
    status = _get_first(filters, "status", "statusLabel")
    owner = filters.get("owner")
    tags = _get_first(filters, "tag", "tags")
    if isinstance(tags, str):
        tags = [tags]

    results: list[dict[str, Any]] = []
    for profile in agents:
        if agent_id and str(profile.agent_id) != str(agent_id):
            continue
        if status and str(profile.status) != str(status):
            continue
        if owner and str(profile.owner) != str(owner):
            continue
        if tags:
            profile_tags = set(profile.tags)
            required = set(str(tag) for tag in tags if tag)
            if required and not required.issubset(profile_tags):
                continue
        results.append(_serialise_agent(profile))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-id")
    parser.add_argument("--status")
    parser.add_argument("--owner")
    parser.add_argument("--tag", action="append", dest="tag")
    parser.add_argument("--registry-path")

    args = parser.parse_args()
    env_inputs = _load_env_inputs()
    merged_inputs = _merge_inputs(env_inputs, vars(args))

    registry_value = _get_first(merged_inputs, "registry_path", "registryPath")
    registry_path = Path(registry_value or DEFAULT_REGISTRY)
    registry_path = registry_path.expanduser().resolve()

    try:
        registry = AgentRegistry(registry_path)
        agents = _filter_agents(registry, merged_inputs)
    except Exception as exc:  # pragma: no cover - surfaced to operator
        print(json.dumps({"status": "failed", "error": str(exc)}))
        return 1

    print(
        json.dumps(
            {
                "status": "success",
                "registryPath": str(registry_path),
                "count": len(agents),
                "agents": agents,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
