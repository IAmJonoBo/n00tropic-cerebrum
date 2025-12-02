#!/usr/bin/env python3
"""Validate n00man agent profiles via the governance engine."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[4]
N00MAN_ROOT = ROOT / "n00man"
DOCS_ROOT = N00MAN_ROOT / "docs"
DEFAULT_REGISTRY = DOCS_ROOT / "agent-registry.json"

sys.path.insert(0, str(ROOT))

from n00man.core import AgentGovernanceError, AgentGovernanceValidator  # noqa: E402
from n00man.core.profile import (  # noqa: E402
    AgentCapability,
    AgentGuardrail,
    AgentProfile,
)
from n00man.core.registry import AgentRegistry  # noqa: E402


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


def _profile_from_payload(payload: Dict[str, Any]) -> AgentProfile:
    caps = [AgentCapability(**entry) for entry in payload.get("capabilities", [])]
    guardrails = [AgentGuardrail(**entry) for entry in payload.get("guardrails", [])]
    profile_fields = {
        key: value
        for key, value in payload.items()
        if key not in {"capabilities", "guardrails"}
    }
    return AgentProfile(capabilities=caps, guardrails=guardrails, **profile_fields)


def _load_profile(inputs: Dict[str, Any]) -> AgentProfile:
    profile_path = _get_first(inputs, "profile_path", "profilePath")
    if profile_path:
        path = Path(str(profile_path)).expanduser().resolve()
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise SystemExit("profile_path must point to a JSON object")
        return _profile_from_payload(payload)

    agent_id = _get_first(inputs, "agent_id", "agentId", "name")
    if not agent_id:
        raise SystemExit("agent_id or profile_path is required")
    registry_value = _get_first(inputs, "registry_path", "registryPath")
    registry_path = Path(registry_value or DEFAULT_REGISTRY)
    registry = AgentRegistry(registry_path)
    profile = registry.get(str(agent_id))
    if not profile:
        raise SystemExit(f"Agent '{agent_id}' not found in registry {registry_path}")
    return profile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-id")
    parser.add_argument("--profile-path")
    parser.add_argument("--registry-path")
    parser.add_argument("--schema-path")
    parser.add_argument("--roles-path")

    args = parser.parse_args()
    env_inputs = _load_env_inputs()
    merged_inputs = _merge_inputs(env_inputs, vars(args))

    schema_raw = _get_first(merged_inputs, "schema_path", "schemaPath")
    schema_path = Path(str(schema_raw)).expanduser().resolve() if schema_raw else None
    roles_raw = _get_first(merged_inputs, "roles_path", "rolesPath")
    roles_path = Path(str(roles_raw)).expanduser().resolve() if roles_raw else None

    try:
        profile = _load_profile(merged_inputs)
        validator = AgentGovernanceValidator(
            schema_path=schema_path,
            roles_path=roles_path,
        )
        validator.validate(profile)
    except AgentGovernanceError as exc:
        print(
            json.dumps(
                {"status": "failed", "agentId": profile.agent_id, "error": str(exc)}
            )
        )
        return 2
    except Exception as exc:  # pragma: no cover
        error_payload = {"status": "failed", "error": str(exc)}
        if "profile" in locals():
            error_payload["agentId"] = getattr(profile, "agent_id", "unknown")
        print(json.dumps(error_payload))
        return 1

    print(
        json.dumps(
            {
                "status": "success",
                "agentId": profile.agent_id,
                "role": profile.role,
                "statusLabel": profile.status,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
