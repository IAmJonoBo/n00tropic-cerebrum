#!/usr/bin/env python3
"""Generate a report for each top-level repo about Renovate & skeletons.

Output: CSV with fields repo,has_renovate_json,extends_contains_central,has_package_json,has_pyproject,has_requirements,trunk_has_renovate,templates_present
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CENTRAL_EXTEND_GITHUB = (
    "github>n00tropic/n00tropic-cerebrum//renovate-presets/workspace.json"
)
CENTRAL_EXTEND_LOCAL = "local>renovate-presets/workspace.json"


def _check_renovate_extend(renovate: Path) -> bool:
    try:
        cfg = json.loads(renovate.read_text(encoding="utf-8"))
        extends = cfg.get("extends") or []
        if isinstance(extends, str):
            extends = [extends]
        for e in extends:
            if CENTRAL_EXTEND_GITHUB in e or CENTRAL_EXTEND_LOCAL in e:
                return True
    except Exception:
        return False
    return False


def _check_file_exists(repo: Path, name: str) -> bool:
    return (repo / name).exists()


def _check_trunk_has_renovate(trunk: Path) -> bool:
    try:
        payload = trunk.read_text(encoding="utf-8")
        if "renovate@" in payload or "renovate:" in payload or "renovate" in payload:
            return True
    except Exception:
        return False
    return False


def examine_repo(repo: Path) -> dict:
    data = {
        "repo": repo.name,
        "has_renovate_json": False,
        "extends_contains_central": False,
        "has_package_json": False,
        "has_pyproject": False,
        "has_requirements": False,
        "trunk_has_renovate": False,
        "templates_present": False,
    }
    renovate = repo / "renovate.json"
    if _check_file_exists(repo, "renovate.json"):
        data["has_renovate_json"] = True
        data["extends_contains_central"] = _check_renovate_extend(renovate)
    data["has_package_json"] = _check_file_exists(repo, "package.json")
    data["has_pyproject"] = _check_file_exists(repo, "pyproject.toml")
    data["has_requirements"] = _check_file_exists(repo, "requirements.txt")
    trunk = repo / ".trunk" / "trunk.yaml"
    if trunk.exists():
        data["trunk_has_renovate"] = _check_trunk_has_renovate(trunk)
    data["templates_present"] = _check_file_exists(
        repo, "templates"
    ) or _check_file_exists(repo, "exports")
    return data


def main() -> int:
    out = []
    for p in sorted(ROOT.iterdir()):
        if not p.is_dir():
            continue
        name = p.name
        if name in (
            ".git",
            ".venv-workspace",
            "artifacts",
            "build",
            "node_modules",
            "docs",
            "packages",
        ):
            continue
        # skip workspace support dirs
        if name.startswith("."):
            continue
        out.append(examine_repo(p))

    try:
        if not out:
            print("No repositories discovered; no report generated.")
            return 0
        with open(
            ".dev/automation/artifacts/subrepo-state.csv", "w", encoding="utf-8"
        ) as fh:
            w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
            w.writeheader()
            for row in out:
                w.writerow(row)
    except Exception as e:
        print(f"Failed to generate report: {e}")
        return 1
    print("Report written to .dev/automation/artifacts/subrepo-state.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
