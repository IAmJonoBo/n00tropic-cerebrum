#!/usr/bin/env python3
# pylint: disable=missing-function-docstring,line-too-long,invalid-name
"""Cross-repo guardrail checks for the n00tropic Cerebrum workspace."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT: Path = Path(__file__).resolve().parents[3]
TOOLCHAIN_MANIFEST = ROOT / "n00-cortex" / "data" / "toolchain-manifest.json"
FRONTIERS_MANIFEST = ROOT / "n00-frontiers" / "templates" / "manifest.json"
FRONTIERS_WORKFLOWS = [
    ROOT / "n00-frontiers" / ".github" / "workflows" / "templates-validate.yml",
    ROOT / "n00-frontiers" / ".github" / "workflows" / "template-e2e.yml",
]
FRONTIERS_TRUNK = ROOT / "n00-frontiers" / ".trunk" / "trunk.yaml"
FRONTIERS_EXPORT_ROOT = ROOT / "n00-frontiers" / "exports" / "cortex"
FRONTIERS_EXPORT_TEMPLATES = FRONTIERS_EXPORT_ROOT / "templates" / "cookiecutter.json"
FRONTIERS_EXPORT_METADATA = FRONTIERS_EXPORT_ROOT / "metadata.json"
FRONTIERS_EXPORT_ASSETS = FRONTIERS_EXPORT_ROOT / "assets" / "index.json"
CANONICAL_TRUNK = (
    ROOT / "n00-cortex" / "data" / "trunk" / "base" / ".trunk" / "trunk.yaml"
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
RENOVATE_FILES: Dict[str, Tuple[Path, str]] = {
    "n00-cortex": (
        ROOT / "n00-cortex" / "renovate.json",
        "local>renovate-presets/workspace.json",
    ),
    "n00-frontiers": (
        ROOT / "n00-frontiers" / "renovate.json",
        "github>IAmJonoBo/n00-cortex//renovate-presets/workspace.json",
    ),
    "n00plicate": (
        ROOT / "n00plicate" / "renovate.json",
        "github>IAmJonoBo/n00-cortex//renovate-presets/workspace.json",
    ),
}
TRUNK_LINTER_COMMENT = re.compile(r"\s+#.*$")


def _discover_trunk_targets() -> Dict[str, Path]:
    targets: Dict[str, Path] = {}
    for trunk_file in ROOT.glob("*/.trunk/trunk.yaml"):
        repo = trunk_file.parent.parent.name
        targets[repo] = trunk_file
    return dict(sorted(targets.items()))


def _parse_trunk_linters(payload: str) -> Dict[str, str | None]:
    linters: Dict[str, str | None] = {}
    in_enabled_block = False
    for raw_line in payload.splitlines():
        if not raw_line.strip():
            continue
        if raw_line.lstrip().startswith("#"):
            continue
        if raw_line.startswith("lint:"):
            in_enabled_block = False
            continue
        if raw_line.startswith("  enabled:"):
            in_enabled_block = True
            continue
        if raw_line.startswith("  disabled:") or raw_line.startswith("actions:"):
            in_enabled_block = False
        if not in_enabled_block:
            continue
        stripped = raw_line.strip()
        if not stripped.startswith("- "):
            continue
        entry = stripped[2:]
        entry = TRUNK_LINTER_COMMENT.sub("", entry).strip()
        if not entry:
            continue
        if "@" in entry:
            tool, version = entry.split("@", 1)
            linters[tool.strip()] = version.strip()
        else:
            linters[entry.strip()] = None
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
                f"{repo}/.trunk/trunk.yaml pins {tool}@{downstream_version}, expected {version}."
            )
    for tool, version in downstream.items():
        if tool not in canonical:
            if version is None:
                messages.append(
                    f"{repo}/.trunk/trunk.yaml enables {tool}, which is not present in canonical. "
                    "Update the canonical config or justify the override."
                )
            else:
                messages.append(
                    f"{repo}/.trunk/trunk.yaml enables {tool}@{version}, which is not present in canonical. "
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
                yield match.group(1)


def _extract_trunk_runtime(path: Path, runtime: str) -> Iterable[str]:
    pattern = re.compile(rf"^\s*-\s*{re.escape(runtime)}@([0-9][0-9.\-]*)\s*$")
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            match = pattern.search(line)
            if match:
                yield match.group(1)


def _load_overrides() -> Dict[str, Dict[str, str]]:
    overrides: Dict[str, Dict[str, str]] = {}
    if not OVERRIDE_DIR.exists():
        return overrides
    for manifest_path in sorted(OVERRIDE_DIR.glob("*.json")):
        data = _load_json(manifest_path)
        project = data.get("project")
        if not isinstance(project, str):
            continue
        project_overrides: Dict[str, str] = {}
        for tool, details in (data.get("overrides") or {}).items():
            if isinstance(details, dict) and isinstance(details.get("version"), str):
                project_overrides[tool] = details["version"]
        if project_overrides:
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
    overrides: Dict[str, Dict[str, str]],
    errors: list[str],
) -> str | None:
    override = overrides.get(project, {}).get(tool)
    if override and canonical:
        if _version_tuple(override) < _version_tuple(canonical):
            errors.append(
                f"Override for {project} {tool} ({override}) is lower than canonical {canonical}."
            )
        return override
    if override:
        return override
    return canonical


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
    toolchains = manifest.get("toolchains", {})
    python_version_canonical = toolchains.get("python", {}).get("version")
    node_version_canonical = toolchains.get("node", {}).get("version")
    go_version_canonical = toolchains.get("go", {}).get("version")
    metadata["toolchains"] = toolchains

    repos = manifest.get("repos", {})
    if isinstance(repos, dict):
        metadata["repositories"] = len(repos)

    overrides = _load_overrides()
    if overrides:
        metadata["overrides"] = overrides

    if not FRONTIERS_MANIFEST.exists():
        errors.append(
            "n00-frontiers/templates/manifest.json not found. Run sync_manifest first."
        )
    else:
        frontiers_manifest = _load_json(FRONTIERS_MANIFEST)
        templates = frontiers_manifest.get("templates", {})

        python_ctx = templates.get("python-service", {}).get("sample_contexts", {})
        for name, ctx in python_ctx.items():
            declared = ctx.get("python_version")
            expected_python = _effective_version(
                "n00-frontiers", "python", python_version_canonical, overrides, errors
            )
            if expected_python and declared and str(declared) != expected_python:
                errors.append(
                    f"python-service sample context '{name}' pins python_version={declared}, "
                    f"expected {expected_python}."
                )

        node_ctx = templates.get("node-service", {}).get("sample_contexts", {})
        for name, ctx in node_ctx.items():
            declared = ctx.get("node_version")
            expected_node = _effective_version(
                "n00-frontiers", "node", node_version_canonical, overrides, errors
            )
            if expected_node and declared and str(declared) != expected_node:
                errors.append(
                    f"node-service sample context '{name}' pins node_version={declared}, expected {expected_node}."
                )

    for workflow in FRONTIERS_WORKFLOWS:
        if not workflow.exists():
            errors.append(f"Workflow missing: {workflow}")
            continue
        for declared in _extract_workflow_node_version(workflow):
            expected_node = _effective_version(
                "n00-frontiers", "node", node_version_canonical, overrides, errors
            )
            if expected_node and declared != expected_node:
                errors.append(
                    f"{workflow.name} sets node-version={declared}, expected {expected_node}."
                )

    canonical_payload = None
    canonical_linters: Dict[str, str | None] = {}
    if not CANONICAL_TRUNK.exists():
        errors.append(f"Canonical Trunk config missing at {CANONICAL_TRUNK}")
    else:
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
                errors.append(
                    f"{repo}/.trunk/trunk.yaml diverges from canonical copy in "
                    "n00-cortex/data/trunk/base/.trunk/trunk.yaml. "
                    f"Run .dev/automation/scripts/sync-trunk.py --pull --repo {repo}."
                )
            for message in _diff_trunk_linters(
                repo, canonical_linters, downstream_payload
            ):
                errors.append(message)

    if FRONTIERS_TRUNK.exists():
        expected_python = _effective_version(
            "n00-frontiers", "python", python_version_canonical, overrides, errors
        )
        expected_node = _effective_version(
            "n00-frontiers", "node", node_version_canonical, overrides, errors
        )
        expected_go = _effective_version(
            "n00-frontiers", "go", go_version_canonical, overrides, errors
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
    else:
        errors.append(f"Missing Trunk config at {FRONTIERS_TRUNK}")

    if FRONTIERS_EXPORT_TEMPLATES.exists():
        raw_templates = _load_json(FRONTIERS_EXPORT_TEMPLATES)
        if isinstance(raw_templates, list):
            normalised_templates: List[Dict[str, object]] = [
                _normalise_frontiers_template(entry)
                for entry in raw_templates
                if isinstance(entry, dict)
            ]
        else:
            normalised_templates = []
        metadata["frontiersTemplates"] = len(normalised_templates)

        if not CORTEX_FRONTIERS_TEMPLATES.exists():
            errors.append(
                f"n00-cortex/catalog missing frontiers templates at {CORTEX_FRONTIERS_TEMPLATES}. "
                "Run npm run ingest:frontiers."
            )
        else:
            cortex_templates = _load_json(CORTEX_FRONTIERS_TEMPLATES)
            if cortex_templates != normalised_templates:
                errors.append(
                    "n00-cortex/data/catalog/frontiers-templates.json is out of sync with "
                    "n00-frontiers exports. Run npm run ingest:frontiers."
                )

        expected_ids = [entry.get("id") for entry in normalised_templates]
        index_path = CORTEX_FRONTIERS_EXPORT_DIR / "index.json"
        if not index_path.exists():
            errors.append(
                f"n00-cortex missing frontiers template index at {index_path}. "
                "Run npm run ingest:frontiers."
            )
        else:
            index_payload = _load_json(index_path)
            if index_payload != expected_ids:
                errors.append(
                    "n00-cortex/data/exports/frontiers/templates/index.json does not match "
                    "the n00-frontiers export. Run npm run ingest:frontiers."
                )

        if not CORTEX_FRONTIERS_EXPORT_DIR.exists():
            errors.append(
                f"n00-cortex missing frontiers template exports directory at {CORTEX_FRONTIERS_EXPORT_DIR}."
            )
        else:
            for entry in normalised_templates:
                slug = entry.get("id")
                if not slug:
                    continue
                template_path = CORTEX_FRONTIERS_EXPORT_DIR / f"{slug}.json"
                if not template_path.exists():
                    errors.append(
                        f"Missing exported template for '{slug}' at {template_path}. "
                        "Run npm run ingest:frontiers."
                    )
                    continue
                template_payload = _load_json(template_path)
                if template_payload != entry:
                    errors.append(
                        f"Exported template '{slug}' differs from n00-frontiers catalog. "
                        "Run npm run ingest:frontiers."
                    )

        if FRONTIERS_EXPORT_METADATA.exists():
            metadata_payload = _load_json(FRONTIERS_EXPORT_METADATA)
            if not CORTEX_FRONTIERS_METADATA.exists():
                errors.append(
                    f"n00-cortex missing frontiers metadata at {CORTEX_FRONTIERS_METADATA}. "
                    "Run npm run ingest:frontiers."
                )
            elif _load_json(CORTEX_FRONTIERS_METADATA) != metadata_payload:
                errors.append(
                    "n00-cortex/data/catalog/frontiers-metadata.json is out of sync with n00-frontiers exports. "
                    "Run npm run ingest:frontiers."
                )

        if FRONTIERS_EXPORT_ASSETS.exists():
            assets_payload = _load_json(FRONTIERS_EXPORT_ASSETS)
            if not CORTEX_FRONTIERS_ASSETS.exists():
                errors.append(
                    f"n00-cortex missing frontiers assets catalog at {CORTEX_FRONTIERS_ASSETS}. "
                    "Run npm run ingest:frontiers."
                )
            elif _load_json(CORTEX_FRONTIERS_ASSETS) != assets_payload:
                errors.append(
                    "n00-cortex/data/catalog/frontiers-assets.json is out of sync with n00-frontiers exports. "
                    "Run npm run ingest:frontiers."
                )
    else:
        errors.append(
            f"n00-frontiers exports not generated at {FRONTIERS_EXPORT_TEMPLATES}. "
            "Run python tools/export_cortex_assets.py."
        )

    if PROJECT_KITS.exists() and BOILERPLATES.exists():
        project_kits = _load_json(PROJECT_KITS)
        boilerplates = _load_json(BOILERPLATES)
        boilerplate_versions = {
            item["boilerplate_id"]: item.get("version")
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
                if _version_tuple(current) < _version_tuple(minimum):
                    errors.append(
                        f"Project kit '{kit.get('kit_id')}' expects {target}>={minimum}, "
                        f"but catalog reports {current}."
                    )

    for repo, (path, expected_extend) in RENOVATE_FILES.items():
        if not path.exists():
            errors.append(f"{repo} missing renovate.json at {path}.")
            continue
        config = _load_json(path)
        extends = config.get("extends", [])
        if expected_extend not in extends:
            errors.append(f"{repo} renovate.json does not extend '{expected_extend}'.")

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
