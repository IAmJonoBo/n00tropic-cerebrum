"""Data models for MCP federation manifest (module registry)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from pydantic import BaseModel, ConfigDict, Field


class HealthCommand(BaseModel):
    label: str
    command: List[str]
    env: dict[str, str] = Field(default_factory=dict)
    timeoutSeconds: int = Field(60, ge=5, le=1800)


class ModuleHealth(BaseModel):
    commands: List[HealthCommand] = Field(default_factory=list)


class FederatedModule(BaseModel):
    id: str
    summary: str
    manifest: str
    repoRoot: str = "."
    tags: List[str] = Field(default_factory=list)
    includeInRoot: bool = True
    health: ModuleHealth = Field(default_factory=ModuleHealth)

    def manifest_path(self, repo_root: Path) -> Path:
        base = repo_root / self.manifest
        return base.resolve()

    def repo_path(self, repo_root: Path) -> Path:
        base = repo_root / self.repoRoot
        return base.resolve()


class FederationManifest(BaseModel):
    version: str
    modules: List[FederatedModule]

    model_config = ConfigDict(extra="allow")

    @classmethod
    def load(cls, manifest_path: Path, repo_root: Path) -> "FederationManifest":
        data = manifest_path.read_text(encoding="utf-8")
        manifest = cls.model_validate_json(data)
        manifest._validate(repo_root)
        return manifest

    def _validate(self, repo_root: Path) -> None:
        seen_ids: set[str] = set()
        for module in self.modules:
            if module.id in seen_ids:
                raise ValueError(f"Duplicate module id detected: {module.id}")
            seen_ids.add(module.id)
            manifest_path = module.manifest_path(repo_root)
            if not manifest_path.exists():
                raise FileNotFoundError(
                    f"Federated module {module.id} manifest missing: {manifest_path}"
                )
            repo_path = module.repo_path(repo_root)
            if not repo_path.exists():
                raise FileNotFoundError(
                    f"Federated module {module.id} repo root missing: {repo_path}"
                )

    def included_modules(self) -> Iterable[FederatedModule]:
        return (mod for mod in self.modules if mod.includeInRoot)

    def module_index(self, repo_root: Path) -> list[dict[str, str]]:
        index: list[dict[str, str]] = []
        for module in self.modules:
            index.append(
                {
                    "id": module.id,
                    "summary": module.summary,
                    "manifest": str(module.manifest_path(repo_root)),
                    "repoRoot": str(module.repo_path(repo_root)),
                    "tags": ",".join(module.tags),
                    "includeInRoot": str(module.includeInRoot).lower(),
                }
            )
        return index
