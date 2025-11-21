#!/usr/bin/env python3
"""Synchronise Trunk config from canonical and optionally create PRs in subrepos.

This is a convenience helper that automates `sync-trunk.py --pull` and opens PRs
for repos whose `.trunk/trunk.yaml` changed. It is intentionally opt-in via
`--apply` to avoid unexpected repository mutations.
"""
from __future__ import annotations

import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[3]
SYNC_SCRIPT = ROOT / ".dev" / "automation" / "scripts" / "sync-trunk.py"


def _find_changed_repos() -> List[str]:
    changed = []
    for p in sorted(ROOT.iterdir()):
        if not p.is_dir():
            continue
        trunk = p / ".trunk" / "trunk.yaml"
        if trunk.exists():
            git = ["git", "-C", str(p), "status", "--porcelain"]
            out = subprocess.run(git, capture_output=True, text=True)
            if out.returncode == 0 and out.stdout.strip():
                changed.append(p.name)
    return changed


def _apply_changes_for_repo(repo: str) -> None:
    path = ROOT / repo
    branch = f"chore/sync-trunk/{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
    subprocess.run(["git", "-C", str(path), "checkout", "-b", branch], check=True)
    subprocess.run(["git", "-C", str(path), "add", ".trunk/trunk.yaml"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "commit",
            "-m",
            "chore(trunk): sync trunk.yaml from canonical",
        ],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "push", "--set-upstream", "origin", branch], check=True
    )
    title = "chore(trunk): sync trunk.yaml from canonical"
    body = "Automated trunk sync from canonical trunk.yaml (n00-cortex) via `sync-trunk.py`."
    subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            f"n00tropic/{repo}",
            "--base",
            "main",
            "--head",
            branch,
            "--title",
            title,
            "--body",
            body,
        ],
        check=True,
    )
    print(f"Created PR for {repo}: {title}")


def run_sync(repos: Optional[List[str]] = None, apply_changes: bool = False) -> int:
    args = ["python3", str(SYNC_SCRIPT), "--pull"]
    if repos:
        for r in repos:
            args.extend(["--repo", r])
    print("Running:", " ".join(args))
    res = subprocess.run(args, check=False)
    if res.returncode != 0:
        print("sync-trunk reported non-zero exit code; aborting autopush")
        return res.returncode

    # Find repos with updated trunk.yaml by checking git status in each repo dir
    changed_repos = _find_changed_repos()

    if not changed_repos:
        print("No changes detected after running sync-trunk; nothing to push")
        return 0

    if not apply_changes:
        print("Dry-run: would create PRs for:", changed_repos)
        return 0

    # Apply changes: commit & push each change in its submodule and create PR
    for repo in changed_repos:
        _apply_changes_for_repo(repo)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", action="append", help="Repo to limit to (name)")
    parser.add_argument(
        "--apply", action="store_true", help="Apply changes & create PRs"
    )
    args = parser.parse_args()
    return run_sync(repos=args.repo, apply_changes=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
