"""Agent foundry executor and helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .profile import AgentCapability, AgentProfile
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
        from agent_core import CapabilityExecutor, trace_operation  # type: ignore
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
    guardrails: list[str] | None = None,
    tags: list[str] | None = None,
    owner: str | None = None,
    status: str | None = None,
) -> AgentProfile:
    """Create an AgentProfile from primitive inputs."""
    cap_objs = [
        AgentCapability(
            id=cap.get("id") or f"cap-{idx}",
            name=cap.get("name", "Unnamed"),
            description=cap.get("description", ""),
            parameters=cap.get("parameters", {}),
        )
        for idx, cap in enumerate(capabilities or [])
    ]
    return AgentProfile(
        agent_id=agent_id,
        name=name,
        role=role,
        description=description,
        capabilities=cap_objs,
        model_config=model_config or {},
        guardrails=guardrails or [],
        tags=tags or [],
        owner=owner or "platform-ops",
        status=status or "draft",
    )


class AgentFoundryExecutor(CapabilityExecutor):
    """Capability executor that scaffolds and registers agents."""

    capability_id = "n00man.foundry"
    name = "n00man Agent Foundry"
    version = "0.1.0"
    description = "Scaffold and register n00man agents"
    handler_type = HandlerType.PYTHON
    tags = ["n00man", "foundry", "agents"]

    def __init__(
        self, docs_root: Path | None = None, registry_path: Path | None = None
    ):
        self.docs_root = docs_root or PACKAGE_ROOT / "docs"
        self.registry_path = registry_path or self.docs_root / "agent-registry.json"

    async def execute(
        self,
        *,
        agent_id: str,
        name: str,
        role: str,
        description: str,
        capabilities: list[dict[str, Any]] | None = None,
        model_config: dict[str, Any] | None = None,
        guardrails: list[str] | None = None,
        tags: list[str] | None = None,
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
        )

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
