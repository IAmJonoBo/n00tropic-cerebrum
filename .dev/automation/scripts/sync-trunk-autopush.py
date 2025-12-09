#!/usr/bin/env python3
"""Synchronise Trunk config from canonical and optionally create PRs in subrepos.

This is a convenience helper that automates `sync-trunk.py --pull` and opens PRs
for repos whose `.trunk/trunk.yaml` changed. It is intentionally opt-in via
`--apply` to avoid unexpected repository mutations.
"""
from __future__ import annotations

import argparse
import logging
import re
import shutil
import subprocess
import sys
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[3]
SYNC_SCRIPT = ROOT / ".dev" / "automation" / "scripts" / "sync-trunk.py"


def _runcmd(cmd: List[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run a command and return CompletedProcess, raising on unexpected errors.

    The function maps command names to absolute binaries found on PATH (where applicable)
    to reduce bandit warnings about partial executable names.
    """
    logging.debug("_runcmd: %s (cwd=%s)", cmd, cwd)
    # Map common binaries to absolute path where available
    if cmd and cmd[0] in ("git", "gh"):
        path = shutil.which(cmd[0])
        if path:
            cmd[0] = path
    return subprocess.run(
        cmd,
        cwd=(str(cwd) if cwd else None),
        capture_output=True,
        text=True,
        check=False,
    )


def _find_changed_repos(limit: Optional[Sequence[str]] = None) -> List[str]:
    allowed = set(limit) if limit else None
    changed = []
    for p in sorted(ROOT.iterdir()):
        if not p.is_dir():
            continue
        if allowed and p.name not in allowed:
            continue
        trunk = p / ".trunk" / "trunk.yaml"
        if trunk.exists():
            git = ["git", "-C", str(p), "status", "--porcelain"]
            out = _runcmd(git)
            if out.returncode == 0 and out.stdout.strip():
                changed.append(p.name)
    return changed


def _apply_changes_for_repo(repo: str) -> None:
    if not re.match(r"^[a-zA-Z0-9_-]+$", repo):
        raise RuntimeError(f"Invalid repo name: {repo}")
    path = ROOT / repo
    branch = f"chore/sync-trunk/{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
    logging.info("Creating branch %s in repo %s", branch, repo)
    rc = _runcmd(["git", "-C", str(path), "checkout", "-b", branch])
    if rc.returncode != 0:
        raise RuntimeError(
            f"Failed to create branch {branch} in repo {repo}: {rc.stderr}"
        )
    rc = _runcmd(["git", "-C", str(path), "add", ".trunk/trunk.yaml"])
    if rc.returncode != 0:
        raise RuntimeError(f"Failed to stage trunk.yaml in repo {repo}: {rc.stderr}")
    rc = _runcmd(
        [
            "git",
            "-C",
            str(path),
            "commit",
            "-m",
            "chore(trunk): sync trunk.yaml from canonical",
        ],
    )
    if rc.returncode != 0:
        logging.warning(
            "Warning: commit may have failed (repo=%s): %s", repo, rc.stderr
        )
    rc = _runcmd(["git", "-C", str(path), "push", "--set-upstream", "origin", branch])
    if rc.returncode != 0:
        raise RuntimeError(
            f"Failed to push branch {branch} for repo {repo}: {rc.stderr}"
        )
    title = "chore(trunk): sync trunk.yaml from canonical"
    body = "Automated trunk sync from canonical trunk.yaml (n00-cortex) via `sync-trunk.py`."
    if not shutil.which("gh"):
        logging.warning("gh CLI not found; skipping PR creation for %s", repo)
        return
    rc = _runcmd(
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
        ]
    )
    if rc.returncode != 0:
        raise RuntimeError(f"Failed to create PR for {repo}: {rc.stderr}")
    logging.info("Created PR for %s: %s", repo, title)


def _cleanup_tmp(path: Path) -> None:
    with suppress(FileNotFoundError):
        path.unlink()


def _should_pull_after_check(status: Optional[str], json_path: Path) -> bool:
    if status == "ok":
        print("No Trunk drift detected; nothing to propagate")
        _cleanup_tmp(json_path)
        return False
    if status == "promoted":
        print(
            "Auto-promote detected; canonical trunk.yaml updated from downstream uniform payload"
        )
    else:
        print("Drift detected; pulling canonical trunk.yaml into downstream repos")
    return True


def run_sync(repos: Optional[List[str]] = None, apply_changes: bool = False) -> int:
    import json
    from tempfile import NamedTemporaryFile

    # First: run check with auto-promote enabled to allow downstream uniform payload to become canonical
    check_args = [str(sys.executable), str(SYNC_SCRIPT), "--check", "--auto-promote"]
    pull_args = [str(sys.executable), str(SYNC_SCRIPT), "--pull"]
    tmp = NamedTemporaryFile(prefix="sync-trunk-", suffix=".json", delete=False)
    tmp.close()
    json_path = Path(tmp.name)
    check_args.extend(["--json", str(json_path)])
    if repos:
        for repo in repos:
            check_args.extend(["--repo", repo])
            pull_args.extend(["--repo", repo])

    print("Running check (with auto-promote):", " ".join(check_args))
    res = subprocess.run(check_args, check=False)
    if res.returncode != 0:
        print(
            "sync-trunk check reported non-zero exit code; continuing so pull can remediate"
        )

    data = None
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"Failed to parse sync-trunk JSON report: {exc}", file=sys.stderr)

    status = data.get("status") if isinstance(data, dict) else None
    if not _should_pull_after_check(status, json_path):
        return 0

    print("Running pull:", " ".join(pull_args))
    pull_result = subprocess.run(pull_args, check=False)
    if pull_result.returncode != 0:
        print("sync-trunk pull failed; inspect logs above for details", file=sys.stderr)
        _cleanup_tmp(json_path)
        return pull_result.returncode or 1

    # Find repos with updated trunk.yaml by checking git status in each repo dir
    changed_repos = _find_changed_repos(repos)

    if not changed_repos:
        print("No changes detected after running sync-trunk; nothing to push")
        _cleanup_tmp(json_path)
        return 0

    print(f"sync-trunk status report retained at {json_path}")

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
