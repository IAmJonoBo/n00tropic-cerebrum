#!/usr/bin/env python3
"""Validate workspace repos against the skeleton definition."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import yaml


def load_skeleton(skeleton_path: Path) -> Dict[str, object]:
    if not skeleton_path.exists():
        raise SystemExit(f"Skeleton file missing: {skeleton_path}")
    return yaml.safe_load(skeleton_path.read_text(encoding="utf-8")) or {}


def ensure_dir(path: Path, apply: bool) -> bool:
    if path.exists():
        return False
    if apply:
        path.mkdir(parents=True, exist_ok=True)
        gitkeep = path / ".gitkeep"
        gitkeep.touch(exist_ok=True)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Create missing directories + .gitkeep.")
    args = parser.parse_args()

    org_root = Path(__file__).resolve().parents[3]
    skeleton_path = org_root / ".dev" / "automation" / "workspace-skeleton.yaml"
    payload = load_skeleton(skeleton_path)
    repos_obj = payload.get("repos") or {}

    summary: Dict[str, object] = {"status": "ok", "repos": []}
    missing_total = 0

    for name, spec in repos_obj.items():
        if not isinstance(spec, dict):
            continue
        rel_path = spec.get("path")
        required = spec.get("required") or []
        if not rel_path:
            continue
        repo_root = (org_root / str(rel_path)).resolve()
        repo_missing: List[str] = []
        for req in required:
            req_path = repo_root / req
            if ensure_dir(req_path, args.apply):
                repo_missing.append(str(req_path))
        if repo_missing:
            missing_total += len(repo_missing)
            summary["status"] = "attention"
        summary["repos"].append({"name": name, "path": str(repo_root), "missing": repo_missing})

    print(json.dumps(summary, indent=2))
    return 1 if missing_total and not args.apply else 0


if __name__ == "__main__":
    raise SystemExit(main())
