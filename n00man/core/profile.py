"""Agent profile data structures for the n00man foundry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _default_tags() -> list[str]:
    return []


def _default_capabilities() -> list["AgentCapability"]:
    return []


@dataclass
class AgentCapability:
    """Describe a capability that an agent can perform."""

    id: str
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the capability to a JSON-friendly structure."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass
class AgentProfile:
    """Profile definition for an n00man agent."""

    agent_id: str
    name: str
    role: str
    description: str
    version: str = "0.1.0"
    owner: str = "platform-ops"
    status: str = "draft"
    capabilities: list[AgentCapability] = field(default_factory=_default_capabilities)
    model_config: dict[str, Any] = field(default_factory=dict)
    guardrails: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=_default_tags)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the profile to JSON-friendly dict."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "version": self.version,
            "owner": self.owner,
            "status": self.status,
            "capabilities": [cap.to_dict() for cap in self.capabilities],
            "model_config": self.model_config,
            "guardrails": self.guardrails,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    def to_yaml_frontmatter(self) -> str:
        """Generate YAML front matter block for documentation."""
        lines = [
            "---",
            f"id: {self.agent_id}",
            f"title: {self.name}",
            f"role: {self.role}",
            f"version: {self.version}",
            f"owner: {self.owner}",
            f"status: {self.status}",
            "tags:",
        ]
        for tag in self.tags:
            lines.append(f"  - {tag}")
        lines.append("---")
        return "\n".join(lines)
