"""Governance validation utilities for n00man agents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import yaml  # type: ignore[import-not-found]
from jsonschema import Draft202012Validator  # type: ignore[import-not-found]
from jsonschema.exceptions import ValidationError  # type: ignore[import-not-found]

from .profile import AgentProfile

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PACKAGE_ROOT.parent
DEFAULT_SCHEMA = PACKAGE_ROOT / "schemas" / "agent-profile.schema.json"
DEFAULT_ROLES = (
    WORKSPACE_ROOT / "n00-frontiers" / "frontiers" / "policy" / "agent-roles.yml"
)


class AgentGovernanceError(RuntimeError):
    """Raised when an agent profile violates governance expectations."""


class AgentGovernanceValidator:
    """Validate agent profiles against JSON Schema and frontiers policy."""

    def __init__(
        self,
        schema_path: Path | None = None,
        roles_path: Path | None = None,
    ) -> None:
        self.schema_path = schema_path or DEFAULT_SCHEMA
        self.roles_path = roles_path or DEFAULT_ROLES
        self.roles = self._load_roles()
        self.validator = self._build_validator()

    def _load_roles(self) -> list[str]:
        if not self.roles_path.exists():
            raise AgentGovernanceError(
                f"Agent roles file missing at {self.roles_path}. Run frontiers policy sync."
            )
        data = yaml.safe_load(self.roles_path.read_text(encoding="utf-8")) or {}
        roles = [
            str(entry.get("id")) for entry in data.get("roles", []) if entry.get("id")
        ]
        if not roles:
            raise AgentGovernanceError(
                f"No agent roles defined in {self.roles_path}. Add at least one role."
            )
        return roles

    def _build_validator(self) -> Draft202012Validator:
        if not self.schema_path.exists():
            raise AgentGovernanceError(
                f"Agent profile schema missing at {self.schema_path}."
            )
        schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        defs = schema.setdefault("$defs", {})
        defs.setdefault("agentRoles", {})["enum"] = self.roles
        return Draft202012Validator(schema)

    def validate(self, profile: AgentProfile) -> None:
        errors = self.collect_errors(profile.to_dict())
        if errors:
            raise AgentGovernanceError("\n".join(errors))

    def validate_payload(self, payload: dict[str, Any]) -> None:
        """Validate a raw profile dictionary without constructing AgentProfile."""

        errors = self.collect_errors(payload)
        if errors:
            raise AgentGovernanceError("\n".join(errors))

    def collect_errors(self, payload: dict[str, Any]) -> list[str]:
        """Return all governance violations instead of raising immediately."""

        errors = list(self._iter_error_messages(payload))
        status = payload.get("status")
        guardrails = payload.get("guardrails") or []
        if status in {"beta", "active"} and not guardrails:
            errors.append("guardrails must be defined for beta or active agents")
        if status == "active":
            model_config = payload.get("model_config") or {}
            fallbacks = model_config.get("fallbacks")
            if not fallbacks:
                errors.append("active agents must define at least one fallback model")
        return errors

    def _iter_error_messages(self, payload: dict[str, Any]) -> Iterable[str]:
        for error in self.validator.iter_errors(payload):
            path = ".".join(str(idx) for idx in error.path) or "profile"
            if isinstance(error, ValidationError):
                yield f"{path}: {error.message}"
            else:
                yield f"{path}: {error}"
