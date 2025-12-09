#!/usr/bin/env python3
# pylint: disable=missing-function-docstring,line-too-long,invalid-name
"""Cross-repo guardrail checks for the n00tropic Cerebrum workspace."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Tuple, Union

ROOT: Path = Path(__file__).resolve().parents[3]
TRUNK_DIR_NAME = ".trunk"
TRUNK_CONFIG_FILENAME = "trunk.yaml"
TRUNK_RELATIVE_PATH = f"{TRUNK_DIR_NAME}/{TRUNK_CONFIG_FILENAME}"
RENOVATE_CONFIG_NAME = "renovate.json"
PNPM_STORE_DIR = ".pnpm"
NVMRC_FILENAME = ".nvmrc"
COMMON_SKIP_DIRS = {".git", ".dev", "node_modules", PNPM_STORE_DIR, "artifacts"}
WORKSPACE_IDENTIFIER = "workspace"

TOOLCHAIN_MANIFEST = ROOT / "n00-cortex" / "data" / "toolchain-manifest.json"
FRONTIERS_MANIFEST = ROOT / "n00-frontiers" / "templates" / "manifest.json"
FRONTIERS_WORKFLOWS = [
    ROOT / "n00-frontiers" / ".github" / "workflows" / "templates-validate.yml",
    ROOT / "n00-frontiers" / ".github" / "workflows" / "template-e2e.yml",
]
FRONTIERS_TRUNK = ROOT / "n00-frontiers" / TRUNK_DIR_NAME / TRUNK_CONFIG_FILENAME
FRONTIERS_EXPORT_ROOT = ROOT / "n00-frontiers" / "exports" / "cortex"
FRONTIERS_EXPORT_TEMPLATES = FRONTIERS_EXPORT_ROOT / "templates" / "cookiecutter.json"
FRONTIERS_EXPORT_METADATA = FRONTIERS_EXPORT_ROOT / "metadata.json"
INDEX_FILE_NAME = "index.json"
FRONTIERS_EXPORT_ASSETS = FRONTIERS_EXPORT_ROOT / "assets" / INDEX_FILE_NAME
CANONICAL_TRUNK = (
    ROOT
    / "n00-cortex"
    / "data"
    / "trunk"
    / "base"
    / TRUNK_DIR_NAME
    / TRUNK_CONFIG_FILENAME
)
OVERRIDE_DIR = ROOT / "n00-cortex" / "data" / "dependency-overrides"
PROJECT_KITS = ROOT / "n00-cortex" / "data" / "catalog" / "project-kits.json"
BOILERPLATES = ROOT / "n00-cortex" / "data" / "catalog" / "boilerplates.json"
CORTEX_FRONTIERS_TEMPLATES = (
    ROOT / "n00-cortex" / "data" / "catalog" / "frontiers-templates.json"
)
CORTEX_FRONTIERS_METADATA = (
    ROOT / "n00-cortex" / "data" / "catalog" / "frontiers-metadata.json"
)
CORTEX_FRONTIERS_ASSETS = (
    ROOT / "n00-cortex" / "data" / "catalog" / "frontiers-assets.json"
)
CORTEX_FRONTIERS_EXPORT_DIR = (
    ROOT / "n00-cortex" / "data" / "exports" / "frontiers" / "templates"
)
LOCAL_RENOVATE_PRESET = "local>renovate-presets/workspace.json"
CANONICAL_GITHUB_PRESET = (
    "github>n00tropic/n00tropic-cerebrum//renovate-presets/workspace.json"
)
RENOVATE_FILES: Dict[str, Tuple[Path, Union[str, list[str]]]] = {
    "n00-cortex": (
        ROOT / "n00-cortex" / RENOVATE_CONFIG_NAME,
        LOCAL_RENOVATE_PRESET,
    ),
    "n00-frontiers": (
        ROOT / "n00-frontiers" / RENOVATE_CONFIG_NAME,
        [
            CANONICAL_GITHUB_PRESET,
            "github>n00tropic/n00-cortex//renovate-presets/workspace.json",
        ],
    ),
    "n00plicate": (
        ROOT / "n00plicate" / RENOVATE_CONFIG_NAME,
        [
            CANONICAL_GITHUB_PRESET,
            "github>n00tropic/n00-cortex//renovate-presets/workspace.json",
        ],
    ),
}

# Discover any additional renovate.json files and validate they extend the canonical
# workspace preset (local or via the central GitHub path). This helps ensure the
# repo stays ergonomic and consistent without having to update this script each
# time we add a new repo.
ALLOWED_DOWNGRADES: List[str] = []
FRONTIERS_EXPORT_HINT = "Run python tools/export_cortex_assets.py."
FRONTIERS_INGEST_HINT = "Run npm run ingest:frontiers."
PNPM_SKIP_DIRS = COMMON_SKIP_DIRS | {TRUNK_DIR_NAME, "dist", "build"}
PNPM_SKIP_SUFFIXES = {
    ".md",
    ".adoc",
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".jsonl",
}
TRUNK_SYNC_TEMPLATE = ".dev/automation/scripts/sync-trunk.py --pull --repo {repo}."
WORKFLOW_SKIP_DIRS = COMMON_SKIP_DIRS


@dataclass(frozen=True)
class ToolchainVersions:
    python: str | None
    node: str | None
    go: str | None
    pnpm: str | None


def _tool_version(toolchains: Dict[str, dict], tool: str) -> str | None:
    entry = toolchains.get(tool, {})
    if not isinstance(entry, dict):
        return None
    version = entry.get("version")
    return str(version) if isinstance(version, str) else None


def _build_toolchain_versions(toolchains: Dict[str, dict]) -> ToolchainVersions:
    return ToolchainVersions(
        python=_tool_version(toolchains, "python"),
        node=_tool_version(toolchains, "node"),
        go=_tool_version(toolchains, "go"),
        pnpm=_tool_version(toolchains, "pnpm"),
    )


def _expected_version_value(
    project: str,
    tool: Literal["python", "node", "go"],
    versions: ToolchainVersions,
    overrides: Dict[str, Dict[str, Dict[str, object]]],
    errors: list[str],
) -> str | None:
    canonical = getattr(versions, tool)
    return _effective_version(project, tool, canonical, overrides, errors)


def _trunk_divergence_message(repo: str) -> str:
    return (
        f"{repo}/{TRUNK_RELATIVE_PATH} diverges from canonical copy in "
        f"n00-cortex/data/trunk/base/{TRUNK_RELATIVE_PATH}. "
        f"Run {TRUNK_SYNC_TEMPLATE.format(repo=repo)}"
    )


def _split_tool_version(entry: str) -> tuple[str, str | None]:
    if "@" in entry:
        tool, version = entry.split("@", 1)
        return tool.strip(), version.strip() or None
    return entry.strip(), None


def _parse_override_details(details: object) -> Dict[str, object] | None:
    if not isinstance(details, dict):
        return None
    version = details.get("version")
    if not isinstance(version, str):
        return None
    entry: Dict[str, object] = {"version": version}
    if "allow_lower" in details:
        entry["allow_lower"] = bool(details["allow_lower"])
    return entry


def _load_override_manifest(
    manifest_path: Path,
) -> tuple[str, Dict[str, Dict[str, object]]] | None:
    data = _load_json(manifest_path)
    project = data.get("project")
    overrides = data.get("overrides")
    if not isinstance(project, str) or not isinstance(overrides, dict):
        return None
    parsed: Dict[str, Dict[str, object]] = {}
    for tool, details in overrides.items():
        parsed_entry = _parse_override_details(details)
        if parsed_entry:
            parsed[tool] = parsed_entry
    if not parsed:
        return None
    return project, parsed


class _TrunkLinterTracker:
    def __init__(self) -> None:
        self._in_enabled_block = False

    def consume(self, raw_line: str) -> str | None:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            return None
        if raw_line.startswith("lint:"):
            self._in_enabled_block = False
            return None
        if raw_line.startswith("  enabled:"):
            self._in_enabled_block = True
            return None
        if raw_line.startswith("  disabled:") or raw_line.startswith("actions:"):
            self._in_enabled_block = False
            return None
        if not self._in_enabled_block or not stripped.startswith("- "):
            return None
        payload = stripped[2:]
        entry, _, _ = payload.partition("#")
        cleaned = entry.strip()
        return cleaned or None


def _discover_trunk_targets() -> Dict[str, Path]:
    targets: Dict[str, Path] = {}
    for trunk_file in ROOT.glob(f"*/{TRUNK_RELATIVE_PATH}"):
        repo = trunk_file.parent.parent.name
        targets[repo] = trunk_file
    return dict(sorted(targets.items()))


def _manifest_node_projects(repos: object) -> set[str]:
    if not isinstance(repos, dict):
        return set()
    required: set[str] = set()
    for name, config in repos.items():
        if not isinstance(config, dict):
            continue
        if "node" in config:
            required.add(str(name))
    return required


def _discover_nvmrc_targets() -> Dict[str, Path]:
    targets: Dict[str, Path] = {}
    workspace_path = ROOT / NVMRC_FILENAME
    if workspace_path.exists():
        targets[WORKSPACE_IDENTIFIER] = workspace_path
    for nvmrc in ROOT.glob(f"*/{NVMRC_FILENAME}"):
        if "node_modules" in nvmrc.parts:
            continue
        repo = nvmrc.parent.name
        targets[repo] = nvmrc
    return dict(sorted(targets.items()))


def _normalise_node_version(raw: str) -> str:
    cleaned = raw.strip()
    return cleaned[1:] if cleaned.startswith(("v", "V")) else cleaned


def _required_nvmrc_projects(manifest_repos: object) -> set[str]:
    required = _manifest_node_projects(manifest_repos)
    required.add(WORKSPACE_IDENTIFIER)
    return required


def _missing_nvmrc_message(project: str, expected: str | None) -> str:
    if expected:
        return f"{project} missing {NVMRC_FILENAME} pin for node {expected}."
    return f"{project} missing {NVMRC_FILENAME} to declare node toolchain version."


def _read_nvmrc_payload(
    project: str, path: Path, expected: str | None, errors: list[str]
) -> str | None:
    try:
        declared_raw = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        errors.append(f"Failed to read {path}: {exc}")
        return None
    if declared_raw:
        return declared_raw
    if expected:
        errors.append(f"{project} {NVMRC_FILENAME} is empty; expected node {expected}.")
    else:
        errors.append(f"{project} {NVMRC_FILENAME} is empty; declare a node version.")
    return None


def _validate_required_nvmrc_presence(
    required: set[str],
    targets: Dict[str, Path],
    overrides: Dict[str, Dict[str, Dict[str, object]]],
    versions: ToolchainVersions,
    errors: list[str],
) -> None:
    for project in sorted(required):
        if project in targets:
            continue
        expected = _expected_version_value(project, "node", versions, overrides, errors)
        errors.append(_missing_nvmrc_message(project, expected))


def _parse_trunk_linters(payload: str) -> Dict[str, str | None]:
    linters: Dict[str, str | None] = {}
    tracker = _TrunkLinterTracker()
    for raw_line in payload.splitlines():
        entry = tracker.consume(raw_line)
        if not entry:
            continue
        tool, version = _split_tool_version(entry)
        linters[tool] = version
    return linters


def _diff_trunk_linters(
    repo: str, canonical: Dict[str, str | None], downstream_payload: str
) -> List[str]:
    messages: List[str] = []
    downstream = _parse_trunk_linters(downstream_payload)
    for tool, version in canonical.items():
        downstream_version = downstream.get(tool)
        if version is None:
            continue
        if downstream_version is None:
            continue
        if downstream_version != version:
            messages.append(
                f"{repo}/{TRUNK_RELATIVE_PATH} pins {tool}@{downstream_version}, expected {version}."
            )
    for tool, version in downstream.items():
        if tool not in canonical:
            if version is None:
                messages.append(
                    f"{repo}/{TRUNK_RELATIVE_PATH} enables {tool}, which is not present in canonical. "
                    "Update the canonical config or justify the override."
                )
            else:
                messages.append(
                    f"{repo}/{TRUNK_RELATIVE_PATH} enables {tool}@{version}, which is not present in canonical. "
                    "Update the canonical config or justify the override."
                )
    return messages


def _version_tuple(raw: str) -> Tuple[int, ...]:
    parts: Iterable[str] = raw.split(".")
    numeric = []
    for part in parts:
        if not part:
            continue
        try:
            numeric.append(int(part))
        except ValueError:
            break
    return tuple(numeric)


def _load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _extract_workflow_node_version(path: Path) -> Iterable[str]:
    pattern = re.compile(r'node-version:\s*"([^"]+)"')
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            match = pattern.search(line)
            if match:
                val = match.group(1)
                if "{" in val:
                    continue
                yield val


def _extract_workflow_python_version(path: Path) -> Iterable[str]:
    pattern = re.compile(r'python-version:\s*"([^\"]+)"')
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            match = pattern.search(line)
            if match:
                val = match.group(1)
                if "{" in val:
                    continue
                yield val


def _discover_all_workflows() -> Iterable[Path]:
    for wf in ROOT.glob("**/.github/workflows/*.yml"):
        if set(wf.parts) & WORKFLOW_SKIP_DIRS:
            continue
        yield wf


def _extract_pnpm_versions_in_file(path: Path) -> Iterable[str]:
    # Matches 'corepack prepare pnpm@10.23.0', 'npx -y pnpm@10.23.0', 'npm i -g pnpm@10.23.0'
    pattern = re.compile(r"pnpm@(\d+(?:\.\d+)*)")
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        content = handle.read()
        for match in pattern.finditer(content):
            yield match.group(1)


def _extract_trunk_runtime(path: Path, runtime: str) -> Iterable[str]:
    pattern = re.compile(rf"^\s*-\s*{re.escape(runtime)}@([0-9][0-9.\-]*)\s*$")
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            match = pattern.search(line)
            if match:
                yield match.group(1)


def _load_overrides() -> Dict[str, Dict[str, Dict[str, object]]]:
    overrides: Dict[str, Dict[str, Dict[str, object]]] = {}
    if not OVERRIDE_DIR.exists():
        return overrides
    for manifest_path in sorted(OVERRIDE_DIR.glob("*.json")):
        loaded = _load_override_manifest(manifest_path)
        if not loaded:
            continue
        project, project_overrides = loaded
        overrides[project] = project_overrides
    return overrides


def _normalise_frontiers_template(entry: Dict[str, object]) -> Dict[str, object]:
    return {
        "id": entry.get("id"),
        "name": entry.get("name"),
        "description": entry.get("description"),
        "version": entry.get("version"),
        "language": entry.get("language"),
        "framework": entry.get("framework"),
        "path": entry.get("path"),
        "features": entry.get("features") or [],
        "requirements": entry.get("requirements") or {},
        "usage": entry.get("usage") or {},
        "compliance": entry.get("compliance") or {},
        "tags": entry.get("tags") or [],
    }


def _effective_version(
    project: str,
    tool: str,
    canonical: str | None,
    overrides: Dict[str, Dict[str, Dict[str, object]]],
    errors: list[str],
) -> str | None:
    entry = overrides.get(project, {}).get(tool) or {}
    override = entry.get("version") if isinstance(entry, dict) else None
    allow_lower = bool(entry.get("allow_lower")) if isinstance(entry, dict) else False
    if isinstance(override, str) and canonical:
        if _version_tuple(override) < _version_tuple(canonical):
            if allow_lower:
                ALLOWED_DOWNGRADES.append(
                    f"{project} {tool} {override} < {canonical} (override allowed)"
                )
                return override
            errors.append(
                f"Override for {project} {tool} ({override}) is lower than canonical {canonical}."
            )
        return override
    if isinstance(override, str):
        return override
    return canonical


def _validate_context_block(
    errors: list[str],
    template_name: str,
    contexts: object,
    attr: str,
    label: str,
    expected: str | None,
) -> None:
    if not expected or not isinstance(contexts, dict):
        return
    for name, ctx in contexts.items():
        if not isinstance(ctx, dict):
            continue
        declared = ctx.get(attr)
        if declared and str(declared) != expected:
            errors.append(
                f"{template_name} sample context '{name}' pins {label}={declared}, expected {expected}."
            )


def _validate_frontiers_manifest(
    errors: list[str],
    overrides: Dict[str, Dict[str, Dict[str, object]]],
    versions: ToolchainVersions,
    manifest: dict | None,
) -> None:
    if manifest is None:
        errors.append(
            "n00-frontiers/templates/manifest.json not found. Run sync_manifest first."
        )
        return
    templates = manifest.get("templates", {})
    python_contexts = templates.get("python-service", {}).get("sample_contexts", {})
    node_contexts = templates.get("node-service", {}).get("sample_contexts", {})
    expected_python = _expected_version_value(
        "n00-frontiers", "python", versions, overrides, errors
    )
    expected_node = _expected_version_value(
        "n00-frontiers", "node", versions, overrides, errors
    )
    _validate_context_block(
        errors,
        "python-service",
        python_contexts,
        "python_version",
        "python_version",
        expected_python,
    )
    _validate_context_block(
        errors,
        "node-service",
        node_contexts,
        "node_version",
        "node_version",
        expected_node,
    )


def _validate_frontiers_workflows(
    errors: list[str],
    overrides: Dict[str, Dict[str, Dict[str, object]]],
    versions: ToolchainVersions,
) -> None:
    expected_node = _expected_version_value(
        "n00-frontiers", "node", versions, overrides, errors
    )
    for workflow in FRONTIERS_WORKFLOWS:
        if not workflow.exists():
            errors.append(f"Workflow missing: {workflow}")
            continue
        for declared in _extract_workflow_node_version(workflow):
            if expected_node and declared != expected_node:
                errors.append(
                    f"{workflow.name} sets node-version={declared}, expected {expected_node}."
                )


def _validate_nvmrc_files(
    errors: list[str],
    overrides: Dict[str, Dict[str, Dict[str, object]]],
    versions: ToolchainVersions,
    manifest_repos: object,
    metadata: dict[str, object],
) -> None:
    targets = _discover_nvmrc_targets()
    if targets:
        metadata["nvmrcTargets"] = sorted(targets)
    required = _required_nvmrc_projects(manifest_repos)
    _validate_required_nvmrc_presence(required, targets, overrides, versions, errors)
    for project, path in targets.items():
        expected = _expected_version_value(project, "node", versions, overrides, errors)
        if not expected:
            continue
        declared_raw = _read_nvmrc_payload(project, path, expected, errors)
        if not declared_raw:
            continue
        declared = _normalise_node_version(declared_raw)
        if declared != expected:
            errors.append(
                f"{project} {NVMRC_FILENAME} pins node {declared_raw}, expected {expected}."
            )


def _validate_workflow_file(
    workflow: Path,
    expected_node: str | None,
    expected_python: str | None,
    errors: list[str],
) -> None:
    try:
        for declared_node in _extract_workflow_node_version(workflow):
            if expected_node and declared_node != expected_node:
                errors.append(
                    f"{workflow} sets node-version={declared_node}, expected {expected_node}."
                )
        for declared_py in _extract_workflow_python_version(workflow):
            if not expected_python:
                continue
            exp_major_minor = str(expected_python).split(".")[:2]
            declared_major_minor = str(declared_py).split(".")[:2]
            if exp_major_minor != declared_major_minor:
                errors.append(
                    f"{workflow} sets python-version={declared_py}, expected {expected_python}."
                )
    except OSError as exc:
        errors.append(f"Failed to read {workflow}: {exc}")


def _validate_workspace_workflows(
    errors: list[str],
    overrides: Dict[str, Dict[str, Dict[str, object]]],
    versions: ToolchainVersions,
) -> None:
    expected_node = _expected_version_value(
        "workspace", "node", versions, overrides, errors
    )
    expected_python = _expected_version_value(
        "workspace", "python", versions, overrides, errors
    )
    workflows = sorted(set(_discover_all_workflows()))
    for workflow in workflows:
        _validate_workflow_file(workflow, expected_node, expected_python, errors)
    if versions.pnpm:
        _validate_pnpm_versions(errors, versions.pnpm)


def _validate_pnpm_versions(errors: list[str], expected_pnpm: str) -> None:
    for path in sorted(ROOT.glob("**/*")):
        if not path.is_file():
            continue
        if path.suffix in PNPM_SKIP_SUFFIXES:
            continue
        if set(path.parts) & PNPM_SKIP_DIRS:
            continue
        try:
            for version in _extract_pnpm_versions_in_file(path):
                if version != expected_pnpm:
                    errors.append(
                        f"{path} references pnpm@{version}, expected pnpm@{expected_pnpm}."
                    )
        except OSError:
            continue


def _validate_trunk_configs(
    errors: list[str],
    metadata: dict[str, object],
) -> None:
    if not CANONICAL_TRUNK.exists():
        errors.append(f"Canonical Trunk config missing at {CANONICAL_TRUNK}")
        return
    canonical_payload = CANONICAL_TRUNK.read_text(encoding="utf-8")
    canonical_linters = _parse_trunk_linters(canonical_payload)
    trunk_targets = _discover_trunk_targets()
    metadata["trunkTargets"] = sorted(trunk_targets)
    for repo, path in trunk_targets.items():
        try:
            downstream_payload = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"Failed to read {path}: {exc}")
            continue
        if canonical_payload != downstream_payload:
            errors.append(_trunk_divergence_message(repo))
        for message in _diff_trunk_linters(repo, canonical_linters, downstream_payload):
            errors.append(message)


def _validate_frontiers_trunk_runtime(
    errors: list[str],
    overrides: Dict[str, Dict[str, Dict[str, object]]],
    versions: ToolchainVersions,
) -> None:
    if not FRONTIERS_TRUNK.exists():
        errors.append(f"Missing Trunk config at {FRONTIERS_TRUNK}")
        return
    expected_python = _expected_version_value(
        "n00-frontiers", "python", versions, overrides, errors
    )
    expected_node = _expected_version_value(
        "n00-frontiers", "node", versions, overrides, errors
    )
    expected_go = _expected_version_value(
        "n00-frontiers", "go", versions, overrides, errors
    )
    for declared in _extract_trunk_runtime(FRONTIERS_TRUNK, "python"):
        if expected_python and declared != expected_python:
            errors.append(
                f".trunk runtime python@{declared} does not match expected {expected_python}."
            )
    for declared in _extract_trunk_runtime(FRONTIERS_TRUNK, "node"):
        if expected_node and declared != expected_node:
            errors.append(
                f".trunk runtime node@{declared} does not match expected {expected_node}."
            )
    for declared in _extract_trunk_runtime(FRONTIERS_TRUNK, "go"):
        if expected_go and declared != expected_go:
            errors.append(
                f".trunk runtime go@{declared} does not match expected {expected_go}."
            )


def _ensure_cortex_templates_in_sync(
    errors: list[str], normalised_templates: List[Dict[str, object]]
) -> None:
    if not CORTEX_FRONTIERS_TEMPLATES.exists():
        errors.append(
            f"n00-cortex/catalog missing frontiers templates at {CORTEX_FRONTIERS_TEMPLATES}. "
            f"{FRONTIERS_INGEST_HINT}"
        )
        return
    cortex_templates = _load_json(CORTEX_FRONTIERS_TEMPLATES)
    if not isinstance(cortex_templates, list):
        errors.append(
            "n00-cortex/data/catalog/frontiers-templates.json has unexpected structure. "
            f"{FRONTIERS_INGEST_HINT}"
        )
        return
    if cortex_templates != normalised_templates:
        errors.append(
            "n00-cortex/data/catalog/frontiers-templates.json is out of sync with n00-frontiers exports. "
            f"{FRONTIERS_INGEST_HINT}"
        )


def _ensure_template_index_in_sync(
    errors: list[str], normalised_templates: List[Dict[str, object]]
) -> None:
    index_path = CORTEX_FRONTIERS_EXPORT_DIR / INDEX_FILE_NAME
    expected_ids = [entry.get("id") for entry in normalised_templates]
    if not index_path.exists():
        errors.append(
            f"n00-cortex missing frontiers template index at {index_path}. {FRONTIERS_INGEST_HINT}"
        )
        return
    index_payload = _load_json(index_path)
    if not isinstance(index_payload, list):
        errors.append(
            f"Frontiers template index at {index_path} has unexpected structure. {FRONTIERS_INGEST_HINT}"
        )
        return
    if index_payload != expected_ids:
        errors.append(
            "n00-cortex/data/exports/frontiers/templates/index.json does not match the n00-frontiers export. "
            f"{FRONTIERS_INGEST_HINT}"
        )


def _ensure_template_files(
    errors: list[str], normalised_templates: List[Dict[str, object]]
) -> None:
    if not CORTEX_FRONTIERS_EXPORT_DIR.exists():
        errors.append(
            f"n00-cortex missing frontiers template exports directory at {CORTEX_FRONTIERS_EXPORT_DIR}."
        )
        return
    for entry in normalised_templates:
        slug = entry.get("id")
        if not slug:
            continue
        template_path = CORTEX_FRONTIERS_EXPORT_DIR / f"{slug}.json"
        if not template_path.exists():
            errors.append(
                f"Missing exported template for '{slug}' at {template_path}. {FRONTIERS_INGEST_HINT}"
            )
            continue
        template_payload = _load_json(template_path)
        if template_payload != entry:
            errors.append(
                f"Exported template '{slug}' differs from n00-frontiers catalog. {FRONTIERS_INGEST_HINT}"
            )


def _ensure_metadata_exports(errors: list[str]) -> None:
    if not FRONTIERS_EXPORT_METADATA.exists():
        return
    metadata_payload = _load_json(FRONTIERS_EXPORT_METADATA)
    if not CORTEX_FRONTIERS_METADATA.exists():
        errors.append(
            f"n00-cortex missing frontiers metadata at {CORTEX_FRONTIERS_METADATA}. {FRONTIERS_INGEST_HINT}"
        )
        return
    cortex_payload = _load_json(CORTEX_FRONTIERS_METADATA)
    if cortex_payload != metadata_payload:
        errors.append(
            "n00-cortex/data/catalog/frontiers-metadata.json is out of sync with n00-frontiers exports. "
            f"{FRONTIERS_INGEST_HINT}"
        )


def _ensure_asset_exports(errors: list[str]) -> None:
    if not FRONTIERS_EXPORT_ASSETS.exists():
        return
    assets_payload = _load_json(FRONTIERS_EXPORT_ASSETS)
    if not CORTEX_FRONTIERS_ASSETS.exists():
        errors.append(
            f"n00-cortex missing frontiers assets catalog at {CORTEX_FRONTIERS_ASSETS}. {FRONTIERS_INGEST_HINT}"
        )
        return
    cortex_payload = _load_json(CORTEX_FRONTIERS_ASSETS)
    if cortex_payload != assets_payload:
        errors.append(
            "n00-cortex/data/catalog/frontiers-assets.json is out of sync with n00-frontiers exports. "
            f"{FRONTIERS_INGEST_HINT}"
        )


def _validate_frontiers_exports(
    errors: list[str],
    metadata: dict[str, object],
) -> None:
    if not FRONTIERS_EXPORT_TEMPLATES.exists():
        errors.append(
            f"n00-frontiers exports not generated at {FRONTIERS_EXPORT_TEMPLATES}. {FRONTIERS_EXPORT_HINT}"
        )
        return
    raw_templates = _load_json(FRONTIERS_EXPORT_TEMPLATES)
    normalised_templates: List[Dict[str, object]] = (
        [
            _normalise_frontiers_template(entry)
            for entry in raw_templates
            if isinstance(entry, dict)
        ]
        if isinstance(raw_templates, list)
        else []
    )
    metadata["frontiersTemplates"] = len(normalised_templates)
    _ensure_cortex_templates_in_sync(errors, normalised_templates)
    _ensure_template_index_in_sync(errors, normalised_templates)
    _ensure_template_files(errors, normalised_templates)
    _ensure_metadata_exports(errors)
    _ensure_asset_exports(errors)


def _validate_project_catalog_dependencies(errors: list[str]) -> None:
    if not (PROJECT_KITS.exists() and BOILERPLATES.exists()):
        return
    project_kits = _load_json(PROJECT_KITS)
    boilerplates = _load_json(BOILERPLATES)
    boilerplate_versions = {
        item.get("boilerplate_id"): item.get("version")
        for item in boilerplates
        if isinstance(item, dict)
    }
    for kit in project_kits:
        dependencies = kit.get("dependencies", [])
        for dependency in dependencies:
            if dependency.get("type") != "boilerplate":
                continue
            target = dependency.get("id")
            minimum = dependency.get("minimum_version")
            current = boilerplate_versions.get(target)
            if not target or not minimum or not current:
                continue
            if _version_tuple(str(current)) < _version_tuple(str(minimum)):
                errors.append(
                    f"Project kit '{kit.get('kit_id')}' expects {target}>={minimum}, but catalog reports {current}."
                )


def _validate_renovate_configs(errors: list[str]) -> None:
    for discovered in ROOT.glob(f"*/{RENOVATE_CONFIG_NAME}"):
        repo = discovered.parent.name
        if repo not in RENOVATE_FILES:
            RENOVATE_FILES[repo] = (
                discovered,
                [LOCAL_RENOVATE_PRESET, CANONICAL_GITHUB_PRESET],
            )
    for repo, (path, expected_extend) in RENOVATE_FILES.items():
        if not path.exists():
            errors.append(f"{repo} missing {RENOVATE_CONFIG_NAME} at {path}.")
            continue
        config = _load_json(path)
        extends = config.get("extends", [])
        if isinstance(expected_extend, (list, tuple)):
            if not any(candidate in extends for candidate in expected_extend):
                errors.append(
                    f"{repo} {RENOVATE_CONFIG_NAME} does not extend any of {expected_extend}."
                )
            continue
        if expected_extend not in extends:
            errors.append(
                f"{repo} {RENOVATE_CONFIG_NAME} does not extend '{expected_extend}'."
            )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        dest="json_path",
        type=Path,
        help="Optional file to write a structured JSON report.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    json_path: Path | None = args.json_path
    errors: list[str] = []
    metadata: dict[str, object] = {}

    if not TOOLCHAIN_MANIFEST.exists():
        errors.append(f"Missing toolchain manifest at {TOOLCHAIN_MANIFEST}")
        report(errors, json_path, metadata)
        return 1

    manifest = _load_json(TOOLCHAIN_MANIFEST)
    toolchains_raw = manifest.get("toolchains")
    toolchains = toolchains_raw if isinstance(toolchains_raw, dict) else {}
    metadata["toolchains"] = toolchains
    versions = _build_toolchain_versions(toolchains)

    repos = manifest.get("repos")
    if isinstance(repos, dict):
        metadata["repositories"] = len(repos)

    ALLOWED_DOWNGRADES.clear()
    overrides = _load_overrides()
    if overrides:
        metadata["overrides"] = overrides

    frontiers_manifest = (
        _load_json(FRONTIERS_MANIFEST) if FRONTIERS_MANIFEST.exists() else None
    )
    _validate_frontiers_manifest(errors, overrides, versions, frontiers_manifest)
    _validate_frontiers_workflows(errors, overrides, versions)
    _validate_workspace_workflows(errors, overrides, versions)
    _validate_nvmrc_files(errors, overrides, versions, repos, metadata)
    _validate_trunk_configs(errors, metadata)
    _validate_frontiers_trunk_runtime(errors, overrides, versions)
    _validate_frontiers_exports(errors, metadata)
    _validate_project_catalog_dependencies(errors)
    _validate_renovate_configs(errors)

    if ALLOWED_DOWNGRADES:
        metadata["allowed_downgrades"] = list(ALLOWED_DOWNGRADES)

    report(errors, json_path, metadata)
    return 1 if errors else 0


def report(
    errors: Iterable[str], json_path: Path | None, metadata: dict[str, object]
) -> None:
    findings = list(errors)
    status = "drift" if findings else "ok"
    if not errors:
        print("[cross-check] ✅ Workspace artifacts are in sync.")
    else:
        print("[cross-check] ❌ Detected configuration drift:")
        for issue in errors:
            print(f"  - {issue}")

    if json_path is not None:
        generated = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
        payload = {
            "generated": generated.isoformat().replace("+00:00", "Z"),
            "status": status,
            "findingCount": len(findings),
            "findings": findings,
            "metadata": metadata,
        }
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"[cross-check] Wrote JSON report → {json_path}")


if __name__ == "__main__":
    sys.exit(main())
