"""Generate documentation and executors for n00man agents."""

from __future__ import annotations

import json
from pathlib import Path

from .profile import AgentProfile


class AgentScaffold:
    """Create documentation, manifests, and executor stubs for agents."""

    def __init__(self, docs_root: Path) -> None:
        self.docs_root = docs_root

    def generate(self, profile: AgentProfile) -> list[Path]:
        generated: list[Path] = []
        agent_dir = self.docs_root / "agents" / profile.agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)

        profile_path = agent_dir / "agent-profile.adoc"
        self._write_profile(profile, profile_path)
        generated.append(profile_path)

        manifest_path = agent_dir / "capabilities.json"
        self._write_manifest(profile, manifest_path)
        generated.append(manifest_path)

        executor_path = agent_dir / f"{profile.agent_id.replace('-', '_')}_executor.py"
        self._write_executor(profile, executor_path)
        generated.append(executor_path)

        return generated

    def _write_profile(self, profile: AgentProfile, path: Path) -> None:
        lines = [
            profile.to_yaml_frontmatter(),
            "",
            f"= {profile.name}",
            "",
            profile.description,
            "",
            "== Role",
            "",
            profile.role,
            "",
            "== Capabilities",
            "",
        ]
        for capability in profile.capabilities:
            lines.append(f"=== {capability.name}")
            lines.append("")
            lines.append(capability.description)
            lines.append("")
        lines.append("== Guardrails")
        lines.append("")
        if profile.guardrails:
            for guardrail in profile.guardrails:
                lines.append(f"* {guardrail.to_summary()}")
        else:
            lines.append("* No guardrails defined")
        lines.append("")
        lines.append("== Model Configuration")
        lines.append("")
        lines.append("[source,json]")
        lines.append("----")
        lines.append(json.dumps(profile.model_config, indent=2))
        lines.append("----")
        lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")

    def _write_manifest(self, profile: AgentProfile, path: Path) -> None:
        manifest = {
            "agent_id": profile.agent_id,
            "capabilities": [
                {
                    "id": f"{profile.agent_id}.{cap.id}",
                    "name": cap.name,
                    "description": cap.description,
                    "inputs": cap.inputs,
                    "outputs": cap.outputs,
                }
                for cap in profile.capabilities
            ],
        }
        path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    def _write_executor(self, profile: AgentProfile, path: Path) -> None:
        class_name = (
            "".join(word.capitalize() for word in profile.agent_id.split("-"))
            + "Executor"
        )
        template = f'''"""Auto-generated executor for {profile.agent_id}."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import sys

WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
AGENT_CORE_PATH = WORKSPACE_ROOT / "n00t" / "packages" / "agent-core" / "src"
if str(AGENT_CORE_PATH) not in sys.path:
    sys.path.insert(0, str(AGENT_CORE_PATH))

try:
    from agent_core import CapabilityExecutor, trace_operation
    from agent_core.types import HandlerType
except ImportError:  # pragma: no cover - fallback for docs preview
    from contextlib import nullcontext

    class CapabilityExecutor:
        capability_id = ""

        async def execute(self, **inputs: Any) -> dict[str, Any]:
            raise NotImplementedError

    class HandlerType:
        PYTHON = "python"

    def trace_operation(*_args, **_kwargs):
        return nullcontext()


class {class_name}(CapabilityExecutor):
    """Executor for {profile.name}."""

    capability_id = "{profile.agent_id}"
    name = "{profile.name}"
    version = "{profile.version}"
    description = "{profile.description}"
    handler_type = HandlerType.PYTHON
    tags = {profile.tags!r}

    async def execute(self, **inputs: Any) -> dict[str, Any]:
        with trace_operation(self.capability_id):
            return {{
                "status": "success",
                "agent_id": self.capability_id,
                "message": "Not yet implemented",
                "inputs": inputs,
            }}
'''
        path.write_text(template, encoding="utf-8")
