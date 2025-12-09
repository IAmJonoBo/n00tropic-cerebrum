"""Data models and validation helpers for the MCP capability manifest."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

from pydantic import BaseModel, ConfigDict, Field, model_validator

DEFAULT_ENTRYPOINT_ROOTS: tuple[str, ...] = (
    ".dev/automation/scripts",
    "scripts",
    "n00clear-fusion",
    "n00-horizons",
    "n00-frontiers",
    "n00-cortex",
    "n00-school",
    "n00t",
)
DEFAULT_ALLOWED_ENV: tuple[str, ...] = ("PATH", "PYTHONPATH", "HOME")


class Guardrails(BaseModel):
    max_runtime_seconds: int = Field(900, ge=30, le=7200)
    allowed_exit_codes: List[int] = Field(default_factory=lambda: [0])
    allowed_env: List[str] = Field(default_factory=lambda: list(DEFAULT_ALLOWED_ENV))
    allowed_entrypoint_roots: List[str] = Field(
        default_factory=lambda: list(DEFAULT_ENTRYPOINT_ROOTS)
    )
    allow_network: bool = False
    max_concurrency: int = Field(
        1,
        ge=1,
        le=32,
        description="Maximum concurrent executions of this capability",
    )
    stdout_max_bytes: int = Field(
        8000,
        ge=256,
        le=65536,
        description="Upper bound for captured stdout per run",
    )
    stderr_max_bytes: int = Field(
        8000,
        ge=256,
        le=65536,
        description="Upper bound for captured stderr per run",
    )
    redact_patterns: List[str] = Field(
        default_factory=list,
        description="Regex patterns to redact from stdout/stderr",
    )
    redact_replacement: str = Field(
        "[redacted]",
        min_length=3,
        description="Replacement token for redacted stdout/stderr text",
    )
    telemetry_tags: Dict[str, str] = Field(
        default_factory=dict,
        description="Key/value tags appended to capability telemetry records",
    )

    @model_validator(mode="after")
    def _dedupe_lists(self) -> "Guardrails":  # pragma: no cover - deterministic
        self.allowed_exit_codes = sorted(set(self.allowed_exit_codes))
        self.allowed_env = sorted(set(self.allowed_env))
        self.allowed_entrypoint_roots = sorted(set(self.allowed_entrypoint_roots))
        if self.redact_patterns:
            seen: list[str] = []
            for pattern in self.redact_patterns:
                if not pattern or pattern in seen:
                    continue
                seen.append(pattern)
            self.redact_patterns = seen
        return self


class CapabilityMetadata(BaseModel):
    owner: str | None = Field(
        None, description="Primary maintainer or distribution list"
    )
    tags: List[str] = Field(default_factory=list)
    docs: str | None = None


class Capability(BaseModel):
    id: str
    summary: str
    entrypoint: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    metadata: CapabilityMetadata = Field(
        default_factory=CapabilityMetadata  # type: ignore[arg-type]
    )
    agent: dict[str, Any] = Field(default_factory=dict)
    guardrails: Guardrails = Field(default_factory=Guardrails)  # type: ignore[arg-type]

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def _require_owner_for_mcp(self) -> "Capability":
        if self.is_mcp_enabled() and not self.metadata.owner:
            raise ValueError(
                f"Capability {self.id} requires metadata.owner when MCP is enabled"
            )
        return self

    def resolved_entrypoint(self, repo_root: Path, manifest_dir: Path) -> Path:
        entry_path = Path(self.entrypoint)
        if entry_path.is_absolute():
            raw_path = entry_path
        else:
            raw_path = (manifest_dir / entry_path).resolve()
        if not raw_path.exists():
            msg = f"Capability {self.id} entrypoint missing: {raw_path}"
            raise FileNotFoundError(msg)
        if raw_path.is_dir():
            raise IsADirectoryError(
                f"Capability {self.id} entrypoint is a directory: {raw_path}"
            )
        if raw_path.is_symlink():
            raise RuntimeError(
                f"Capability {self.id} entrypoint must not be a symlink: {raw_path}"
            )
        if repo_root not in raw_path.parents and raw_path != repo_root:
            raise RuntimeError(
                f"Capability {self.id} entrypoint must remain inside repo ({repo_root}); got {raw_path}"
            )

        allowed_roots = [
            repo_root / rel for rel in self.guardrails.allowed_entrypoint_roots
        ]
        if not any(raw_path.is_relative_to(root) for root in allowed_roots):
            allowed_list = ", ".join(str(root) for root in allowed_roots)
            raise RuntimeError(
                f"Capability {self.id} entrypoint {raw_path} not under allowed roots: {allowed_list}"
            )
        return raw_path

    def is_mcp_enabled(self) -> bool:
        agent_cfg = self.agent or {}
        mcp_cfg = agent_cfg.get("mcp") if isinstance(agent_cfg, dict) else None
        return bool(isinstance(mcp_cfg, dict) and mcp_cfg.get("enabled"))


class CapabilityManifest(BaseModel):
    version: str
    agentFramework: dict[str, Any] = Field(default_factory=dict)
    capabilities: List[Capability]

    model_config = ConfigDict(extra="allow")

    @classmethod
    def load(cls, manifest_path: Path, repo_root: Path) -> "CapabilityManifest":
        data = manifest_path.read_text(encoding="utf-8")
        manifest = cls.model_validate_json(data)
        manifest._validate_capabilities(repo_root, manifest_path.parent)
        return manifest

    def _validate_capabilities(self, repo_root: Path, manifest_dir: Path) -> None:
        seen_ids: set[str] = set()
        for cap in self.capabilities:
            if cap.id in seen_ids:
                raise ValueError(f"Duplicate capability id detected: {cap.id}")
            seen_ids.add(cap.id)
            cap.resolved_entrypoint(repo_root, manifest_dir)

    def enabled_capabilities(self) -> Iterable[Capability]:
        return (cap for cap in self.capabilities if cap.is_mcp_enabled())

    def capability_index(self) -> list[dict[str, Any]]:
        index: list[dict[str, Any]] = []
        for cap in self.capabilities:
            entry = {
                "id": cap.id,
                "summary": cap.summary,
                "entrypoint": cap.entrypoint,
                "metadata": cap.metadata.model_dump(),
                "guardrails": cap.guardrails.model_dump(),
                "inputs": cap.inputs,
                "outputs": cap.outputs,
                "agent": cap.agent,
            }
            index.append(entry)
        return index
