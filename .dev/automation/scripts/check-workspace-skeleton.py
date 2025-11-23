#!/usr/bin/env python3
"""Validate workspace repos against the skeleton definition."""

from __future__ import annotations

import argparse
import json
import subprocess
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
    parser.add_argument(
        "--apply", action="store_true", help="Create missing directories + .gitkeep."
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Provision toolchain (pnpm+trunk) and refresh submodules/health after validation.",
    )
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
        expected_branches = spec.get("branches") or []
        if not rel_path:
            continue
        repo_root = (org_root / str(rel_path)).resolve()
        repo_missing: List[str] = []
        for req in required:
            req_path = repo_root / req
            if ensure_dir(req_path, args.apply):
                repo_missing.append(str(req_path))

        branch_missing: List[str] = []
        if expected_branches:
            # Verify remote branches exist (origin required)
            try:
                out = subprocess.check_output(
                    ["git", "-C", str(repo_root), "ls-remote", "--heads", "origin"],
                    text=True,
                )
                remote_heads = {
                    line.split()[1].split("refs/heads/")[-1]
                    for line in out.splitlines()
                    if line.strip()
                }
                for br in expected_branches:
                    if br not in remote_heads:
                        branch_missing.append(br)
            except subprocess.CalledProcessError:
                branch_missing = expected_branches

        if repo_missing:
            missing_total += len(repo_missing)
            summary["status"] = "attention"
        if branch_missing:
            missing_total += len(branch_missing)
            summary["status"] = "attention"
        summary["repos"].append(
            {
                "name": name,
                "path": str(repo_root),
                "missing": repo_missing,
                "missing_branches": branch_missing,
            }
        )

    print(json.dumps(summary, indent=2))

    if args.bootstrap:
        # Provision pnpm + trunk, sync submodules, run trunk check
        subprocess.run([str(org_root / "scripts" / "setup-pnpm.sh")], check=False)
        subprocess.run(
            [str(org_root / "scripts" / "trunk-upgrade-workspace.sh"), "--check"],
            check=False,
        )
        subprocess.run(
            [
                str(
                    org_root / ".dev" / "automation" / "scripts" / "workspace-health.py"
                ),
                "--sync-submodules",
                "--publish-artifact",
            ],
            check=False,
        )

    return 1 if missing_total and not args.apply else 0


if __name__ == "__main__":
    raise SystemExit(main())
