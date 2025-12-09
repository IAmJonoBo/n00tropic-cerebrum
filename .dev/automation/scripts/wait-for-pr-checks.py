#!/usr/bin/env python3
"""Wait for PR checks to complete with a bounded polling loop.

Usage: wait-for-pr-checks.py --pr <number> [--repo owner/repo] [--interval 10] [--max-retries 30]

This utility polls the GitHub PR status using the `gh` CLI and exits with 0 when
all checks report success, 1 when any check fails, and 2 when the max retries
are exhausted.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from typing import Optional


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def get_pr_checks(repo: Optional[str], pr_number: int) -> Optional[dict]:
    cmd = ["gh", "pr", "view", str(pr_number), "--json", "statusCheckRollup"]
    if repo:
        cmd.extend(["--repo", repo])
    res = run(cmd)
    if res.returncode != 0:
        return None
    try:
        data = json.loads(res.stdout)
    except Exception:
        return None
    return data


def checks_completed_and_successful(data: dict) -> Optional[bool]:
    # data contains statusCheckRollup list
    runs = data.get("statusCheckRollup", [])
    if not runs:
        # no checks present (possible), treat as success
        return True
    any_in_progress = any(r.get("status") in ("IN_PROGRESS", "QUEUED") for r in runs)
    if any_in_progress:
        return None
    # If none are in progress, completed. Evaluate conclusions.
    for r in runs:
        conclusion = r.get("conclusion")
        if conclusion and conclusion != "SUCCESS":
            return False
    return True


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pr", type=int, required=True, help="Pull request number to watch"
    )
    parser.add_argument("--repo", help="Repository (owner/repo) to query. Optional")
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Polling interval in seconds (default: 10)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=30,
        help="Maximum retry attempts before exiting (default: 30)",
    )
    args = parser.parse_args(argv)

    attempt = 0
    while attempt < args.max_retries:
        attempt += 1
        data = get_pr_checks(args.repo, args.pr)
        if data is None:
            print(
                f"Attempt {attempt}: Failed to fetch PR data (gh CLI returned error). Retrying in {args.interval}s..."
            )
            time.sleep(args.interval)
            continue
        state = checks_completed_and_successful(data)
        if state is None:
            print(
                f"Attempt {attempt}: Checks are still running. Retrying in {args.interval}s..."
            )
            time.sleep(args.interval)
            continue
        if state is True:
            print(f"Attempt {attempt}: All checks succeeded or none present.")
            return 0
        print(f"Attempt {attempt}: One or more checks failed.")
        return 1

    print(f"Exceeded max retries ({args.max_retries}). Giving up.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
