"""Agent foundry executor and helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .governance import AgentGovernanceValidator
from .profile import AgentCapability, AgentGuardrail, AgentProfile
from .registry import AgentRegistry
from .scaffold import AgentScaffold

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PACKAGE_ROOT.parent
AGENT_CORE_PATH = WORKSPACE_ROOT / "n00t" / "packages" / "agent-core" / "src"
if str(AGENT_CORE_PATH) not in sys.path:
    sys.path.insert(0, str(AGENT_CORE_PATH))

if TYPE_CHECKING:  # pragma: no cover - used for static analysis only
    from agent_core import CapabilityExecutor, trace_operation
    from agent_core.types import HandlerType
else:  # pragma: no cover - runtime import with graceful fallback
    try:
        from agent_core import (  # type: ignore  # isort: skip
            CapabilityExecutor,
            trace_operation,
        )
        from agent_core.types import HandlerType  # type: ignore
    except ImportError:  # pragma: no cover
        from contextlib import contextmanager

        class CapabilityExecutor:  # type: ignore[override]
            capability_id = ""

            async def execute(self, **inputs: Any) -> dict[str, Any]:
                raise NotImplementedError

        class HandlerType:  # type: ignore[override]
            PYTHON = "python"

        @contextmanager
        def trace_operation(*_args, **_kwargs):  # type: ignore[override]
            class _Span:
                def set_attribute(self, *_a, **_kw):
                    return None

            yield _Span()


def build_agent_profile(
    *,
    agent_id: str,
    name: str,
    role: str,
    description: str,
    capabilities: list[dict[str, Any]] | None = None,
    model_config: dict[str, Any] | None = None,
    guardrails: list[dict[str, Any]] | list[str] | None = None,
    tags: list[str] | None = None,
    owner: str | None = None,
    status: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AgentProfile:
    """Create an AgentProfile from primitive inputs."""

    cap_objs = _normalise_capabilities(agent_id, name, description, capabilities)
    guardrail_objs = _normalise_guardrails(agent_id, guardrails)
    profile_model_config = model_config or {
        "provider": "openai",
        "model": "gpt-5.1-codex",
        "fallbacks": ["openai/gpt-5.1-codex-mini"],
    }
    return AgentProfile(
        agent_id=agent_id,
        name=name,
        role=role,
        description=description,
        capabilities=cap_objs,
        model_config=profile_model_config,
        guardrails=guardrail_objs,
        tags=tags or [],
        owner=owner or "platform-ops",
        status=status or "draft",
        metadata=metadata or {},
    )


def _normalise_capabilities(
    agent_id: str,
    name: str,
    description: str,
    capabilities: list[dict[str, Any]] | None,
) -> list[AgentCapability]:
    seed = capabilities or [
        {
            "id": f"{agent_id}-core",
            "name": f"{name} core workflow",
            "description": description,
            "inputs": {
                "instruction": {
                    "type": "string",
                    "description": "Primary task or question",
                }
            },
            "outputs": {
                "artifacts": {
                    "type": "array",
                    "description": "Generated artefacts or responses",
                }
            },
        }
    ]

    cap_objs: list[AgentCapability] = []
    for idx, capability in enumerate(seed, start=1):
        cap_objs.append(
            AgentCapability.from_mapping(
                capability,
                fallback_id=f"cap-{idx}",
                fallback_name=f"{name} capability {idx}",
            )
        )
    return cap_objs


def _normalise_guardrails(
    agent_id: str, guardrails: list[dict[str, Any]] | list[str] | None
) -> list[AgentGuardrail]:
    if not guardrails:
        return []
    guardrail_objs: list[AgentGuardrail] = []
    for idx, guardrail in enumerate(guardrails, start=1):
        if isinstance(guardrail, str):
            guardrail_objs.append(
                AgentGuardrail(
                    id=f"{agent_id}-guardrail-{idx}",
                    description=guardrail,
                )
            )
            continue
        guardrail_objs.append(
            AgentGuardrail(
                id=str(guardrail.get("id") or f"{agent_id}-guardrail-{idx}"),
                description=str(
                    guardrail.get("description")
                    or guardrail.get("id")
                    or "Guardrail description missing"
                ),
                enforcement=str(guardrail.get("enforcement", "required")),
                severity=str(guardrail.get("severity", "medium")),
                owner=guardrail.get("owner"),
            )
        )
    return guardrail_objs


class AgentFoundryExecutor(CapabilityExecutor):
    """Capability executor that scaffolds and registers agents."""

    capability_id = "n00man.foundry"
    name = "n00man Agent Foundry"
    version = "0.1.0"
    description = "Scaffold and register n00man agents"
    handler_type = HandlerType.PYTHON
    tags = ["n00man", "foundry", "agents"]

    def __init__(
        self,
        docs_root: Path | None = None,
        registry_path: Path | None = None,
        schema_path: Path | None = None,
        roles_path: Path | None = None,
    ):
        self.docs_root = docs_root or PACKAGE_ROOT / "docs"
        self.registry_path = registry_path or self.docs_root / "agent-registry.json"
        self.governance = AgentGovernanceValidator(
            schema_path=schema_path, roles_path=roles_path
        )

    async def execute(
        self,
        *,
        agent_id: str,
        name: str,
        role: str,
        description: str,
        capabilities: list[dict[str, Any]] | None = None,
        model_config: dict[str, Any] | None = None,
        guardrails: list[dict[str, Any]] | list[str] | None = None,
        tags: list[str] | None = None,
        owner: str | None = None,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        profile = build_agent_profile(
            agent_id=agent_id,
            name=name,
            role=role,
            description=description,
            capabilities=capabilities,
            model_config=model_config,
            guardrails=guardrails,
            tags=tags,
            owner=owner,
            status=status,
            metadata=metadata,
        )

        self.governance.validate(profile)

        registry = AgentRegistry(self.registry_path)
        registry.register(profile)

        scaffold = AgentScaffold(self.docs_root)
        generated = scaffold.generate(profile)

        with trace_operation(self.capability_id) as span:
            if hasattr(span, "set_attribute"):
                span.set_attribute("agent.id", agent_id)
                span.set_attribute("agent.generated_files", len(generated))

        return {
            "status": "success",
            "agent_id": agent_id,
            "generated_files": [str(path) for path in generated],
            "registry_path": str(self.registry_path),
        }
