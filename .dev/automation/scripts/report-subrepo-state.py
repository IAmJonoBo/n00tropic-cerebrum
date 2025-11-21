#!/usr/bin/env python3
"""Generate a report for each top-level repo about Renovate & skeletons.

Output: CSV with fields repo,has_renovate_json,extends_contains_central,has_package_json,has_pyproject,has_requirements,trunk_has_renovate,templates_present
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[3]
CENTRAL_EXTEND_GITHUB = (
    "github>n00tropic/n00tropic-cerebrum//renovate-presets/workspace.json"
)
CENTRAL_EXTEND_LOCAL = "local>renovate-presets/workspace.json"


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
    if renovate.exists():
        data["has_renovate_json"] = True
        try:
            cfg = json.loads(renovate.read_text(encoding="utf-8"))
            extends = cfg.get("extends") or []
            if isinstance(extends, str):
                extends = [extends]
            for e in extends:
                if CENTRAL_EXTEND_GITHUB in e or CENTRAL_EXTEND_LOCAL in e:
                    data["extends_contains_central"] = True
                    break
        except Exception:
            data["extends_contains_central"] = False
    if (repo / "package.json").exists():
        data["has_package_json"] = True
    if (repo / "pyproject.toml").exists():
        data["has_pyproject"] = True
    if (repo / "requirements.txt").exists():
        data["has_requirements"] = True
    trunk = repo / ".trunk" / "trunk.yaml"
    if trunk.exists():
        payload = trunk.read_text(encoding="utf-8")
        if "renovate@" in payload or "renovate:" in payload or "renovate" in payload:
            data["trunk_has_renovate"] = True
    if (repo / "templates").exists() or (repo / "exports").exists():
        data["templates_present"] = True
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

    w = csv.DictWriter(
        open(".dev/automation/artifacts/subrepo-state.csv", "w", encoding="utf-8"),
        fieldnames=list(out[0].keys()),
    )
    w.writeheader()
    for row in out:
        w.writerow(row)
    print("Report written to .dev/automation/artifacts/subrepo-state.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
