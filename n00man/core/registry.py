"""Agent registry helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from .profile import AgentCapability, AgentGuardrail, AgentProfile


class AgentRegistry:
    """Persist and retrieve agent profiles."""

    def __init__(self, registry_path: Path):
        self.registry_path = registry_path
        self.agents: Dict[str, AgentProfile] = {}
        self._load()

    def _load(self) -> None:
        if not self.registry_path.exists():
            return
        data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        for agent_data in data.get("agents", []):
            caps = [
                AgentCapability(**cap) for cap in agent_data.pop("capabilities", [])
            ]
            guardrails = [
                AgentGuardrail(**guardrail)
                for guardrail in agent_data.pop("guardrails", [])
            ]
            profile = AgentProfile(
                **agent_data,
                capabilities=caps,
                guardrails=guardrails,
            )
            self.agents[profile.agent_id] = profile

    def save(self) -> None:
        payload = {
            "schema_version": "1.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "agents": [profile.to_dict() for profile in self.agents.values()],
        }
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )

    def register(self, profile: AgentProfile) -> None:
        self.agents[profile.agent_id] = profile
        self.save()

    def get(self, agent_id: str) -> AgentProfile | None:
        return self.agents.get(agent_id)

    def list(self) -> list[AgentProfile]:
        return list(self.agents.values())
