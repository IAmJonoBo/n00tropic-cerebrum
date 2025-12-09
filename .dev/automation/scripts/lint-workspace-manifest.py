#!/usr/bin/env python3
"""Lint automation/workspace.manifest.json for required shape and uniqueness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Set

ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = ROOT / "automation" / "workspace.manifest.json"


def load_manifest() -> Dict[str, object]:
    if not MANIFEST_PATH.exists():
        raise SystemExit(f"Manifest missing: {MANIFEST_PATH}")
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # pragma: no cover
        raise SystemExit(f"Unable to parse {MANIFEST_PATH}: {exc}") from exc


def lint_manifest(payload: Dict[str, object]) -> Dict[str, object]:
    errors: List[str] = []
    warnings: List[str] = []

    if "meta" not in payload:
        errors.append("Missing meta section")
    repos = payload.get("repos") or []
    if not isinstance(repos, list):
        errors.append("repos must be a list")
        repos = []

    seen_names: Set[str] = set()
    seen_paths: Set[str] = set()
    repo_summaries: List[Dict[str, object]] = []

    for idx, entry in enumerate(repos):
        if not isinstance(entry, dict):
            errors.append(f"Entry {idx} is not an object")
            continue
        name = entry.get("name")
        path = entry.get("path")
        role = entry.get("role")
        if not name:
            errors.append(f"Entry {idx} missing name")
        if not path:
            errors.append(f"Entry {idx} missing path")
        if not role:
            warnings.append(f"{name or path}: role not set")
        if name in seen_names:
            errors.append(f"Duplicate repo name: {name}")
        if path in seen_paths:
            errors.append(f"Duplicate repo path: {path}")
        if name:
            seen_names.add(name)
        if path:
            seen_paths.add(path)
        repo_summaries.append(
            {
                "name": name,
                "path": path,
                "role": role,
                "has_required": "required" in entry,
                "has_branches": "branches" in entry,
            }
        )

    return {
        "errors": errors,
        "warnings": warnings,
        "repos": repo_summaries,
        "ok": not errors,
    }


def main() -> int:
    payload = load_manifest()
    report = lint_manifest(payload)
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
