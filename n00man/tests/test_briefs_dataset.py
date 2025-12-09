"""Validate example agent briefs stay governance-compliant."""

from __future__ import annotations

import json
from pathlib import Path

from n00man.core import AgentGovernanceValidator, build_agent_profile

BRIEFS_DIR = Path(__file__).resolve().parents[1] / "docs" / "briefs"


def test_example_briefs_validate() -> None:
    validator = AgentGovernanceValidator()
    briefs = sorted(BRIEFS_DIR.glob("*.json"))
    assert briefs, "Expected at least one brief in docs/briefs"
    for brief_path in briefs:
        data = json.loads(brief_path.read_text(encoding="utf-8"))
        profile = build_agent_profile(
            agent_id=data["agent_id"],
            name=data.get("name", data["agent_id"]),
            role=data["role"],
            description=data["description"],
            capabilities=data.get("capabilities"),
            model_config=data.get("model_config"),
            guardrails=data.get("guardrails"),
            tags=data.get("tags"),
            owner=data.get("owner"),
            status=data.get("status"),
            metadata=data.get("metadata"),
        )
        validator.validate(profile)
