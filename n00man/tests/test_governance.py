"""Tests for the agent governance validator."""

from __future__ import annotations

import pytest

from n00man.core import (AgentGovernanceError, AgentGovernanceValidator,
                         build_agent_profile)


def _base_capabilities() -> list[dict[str, object]]:
    return [
        {
            "id": "inspect-artifact",
            "name": "Inspect Artifact",
            "description": "Inspect artefacts for compliance.",
            "inputs": {
                "artifact": {
                    "type": "string",
                    "description": "Path to the artefact under review",
                }
            },
            "outputs": {
                "report": {
                    "type": "object",
                    "description": "Summary of findings",
                }
            },
        }
    ]


def test_validator_accepts_known_role() -> None:
    validator = AgentGovernanceValidator()
    profile = build_agent_profile(
        agent_id="test-analyst",
        name="Test Analyst",
        role="analyst",
        description="Validates evidence and drafts summaries.",
        capabilities=_base_capabilities(),
        guardrails=["Escalate if confidence < 0.7"],
        tags=["analysis"],
    )

    validator.validate(profile)


def test_validator_rejects_unknown_role() -> None:
    validator = AgentGovernanceValidator()
    profile = build_agent_profile(
        agent_id="rogue-agent",
        name="Rogue",
        role="unsupported-role",
        description="Invalid role for governance.",
        capabilities=_base_capabilities(),
    )

    with pytest.raises(AgentGovernanceError):
        validator.validate(profile)


def test_active_agents_require_guardrails_and_fallbacks() -> None:
    validator = AgentGovernanceValidator()
    profile = build_agent_profile(
        agent_id="active-operator",
        name="Active Operator",
        role="operator",
        description="Runs workflows in production.",
        capabilities=_base_capabilities(),
        status="active",
        guardrails=[],
        model_config={
            "provider": "openai",
            "model": "gpt-5.1-codex",
            "fallbacks": [],
        },
    )

    with pytest.raises(AgentGovernanceError):
        validator.validate(profile)
