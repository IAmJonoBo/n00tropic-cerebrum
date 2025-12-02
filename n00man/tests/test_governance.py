"""Tests for the agent governance validator."""

from __future__ import annotations

import pytest

from n00man.core import (
    AgentGovernanceError,
    AgentGovernanceValidator,
    build_agent_profile,
)


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


def test_collect_errors_returns_domain_messages() -> None:
    validator = AgentGovernanceValidator()
    profile = build_agent_profile(
        agent_id="active-reviewer",
        name="Active Reviewer",
        role="reviewer",
        description="Runs final QA reviews.",
        capabilities=_base_capabilities(),
        status="active",
        guardrails=[],
        model_config={
            "provider": "openai",
            "model": "gpt-5.1-codex",
            "fallbacks": [],
        },
    )

    errors = validator.collect_errors(profile.to_dict())

    assert "guardrails must be defined" in "\n".join(errors)
    assert "fallback model" in "\n".join(errors)


def test_validate_payload_accepts_raw_dict() -> None:
    validator = AgentGovernanceValidator()
    profile = build_agent_profile(
        agent_id="beta-analyst",
        name="Beta Analyst",
        role="analyst",
        description="Summarises findings.",
        capabilities=_base_capabilities(),
        guardrails=["Escalate contentious findings"],
    )

    validator.validate_payload(profile.to_dict())
