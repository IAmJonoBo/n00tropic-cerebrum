#!/usr/bin/env python3
"""Wait for GitHub PR checks to finish, with bounded retries and severity-based stop conditions.

Usage:
  python3 wait-for-checks.py --repo n00tropic/n00tropic-cerebrum --pr 7 --interval 10 --max-tries 60 --fail-fast

Defaults:
  interval: 10s
  max-tries: 60 (10 minutes)
  fail-fast: True (stop and return non-zero when any check run concludes as 'failure')

Exits:
  0: all checks succeeded (or became green depending on flags)
  1: failure condition encountered (fail-fast) or any checks finished with non-success
  2: timed out

Notes:
- This script uses the GitHub CLI (gh) to call the API; ensure `gh` is available and authenticated.
- The checks are derived from the commit associated with the PR head ref.
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import time
from typing import Dict, List, Optional, Tuple


def run_command(
    args: List[str], *, capture_output: bool = True
) -> subprocess.CompletedProcess:
    # Use absolute binary for `gh` where possible to reduce risk flagged by security linters.
    return subprocess.run(args, capture_output=capture_output, text=True)


def get_pr_head_sha(owner: str, repo: str, pr_number: int) -> Optional[str]:
    cmd = ["gh", "api", f"/repos/{owner}/{repo}/pulls/{pr_number}"]
    res = run_command(cmd)
    if res.returncode != 0:
        print("Failed to query PR info:", res.stderr.strip())
        return None
    try:
        payload = json.loads(res.stdout)
    except json.JSONDecodeError:
        print("Failed to decode PR JSON payload")
        return None
    return payload.get("head", {}).get("sha")


def get_check_runs(owner: str, repo: str, sha: str) -> Optional[List[Dict[str, str]]]:
    cmd = ["gh", "api", f"/repos/{owner}/{repo}/commits/{sha}/check-runs"]
    res = run_command(cmd)
    if res.returncode != 0:
        print("Failed to query check-runs:", res.stderr.strip())
        return None
    try:
        payload = json.loads(res.stdout)
    except json.JSONDecodeError:
        print("Failed to decode check-runs JSON payload")
        return None
    return payload.get("check_runs", [])


def summarize_check_runs(
    check_runs: List[Dict[str, str]],
) -> Tuple[int, int, int, List[Tuple[str, str, str]]]:
    total = len(check_runs)
    completed = 0
    success = 0
    details = []
    for c in check_runs:
        name = c.get("name", "<unnamed>")
        status = c.get("status")
        conclusion = c.get("conclusion")
        details.append((name, status or "", conclusion or ""))
        if status == "completed":
            completed += 1
            if conclusion == "success":
                success += 1
    return total, completed, success, details


def parse_repo(repo: str) -> Tuple[str, str]:
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return owner, name
    # default owner to n00tropic if not provided
    return "n00tropic", repo


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/repo or repo name")
    parser.add_argument("--pr", type=int, required=True, help="PR number to monitor")
    parser.add_argument(
        "--interval", type=int, default=10, help="Seconds between polls"
    )
    parser.add_argument(
        "--max-tries", type=int, default=60, help="Max polling attempts before timeout"
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        default=True,
        help="Exit early if any check run fails",
    )
    parser.add_argument(
        "--no-fail-fast",
        action="store_true",
        dest="no_fail_fast",
        help="Disable fail-fast behavior",
    )
    parser.add_argument(
        "--fail-on",
        type=str,
        default=",".join(["failure", "cancelled", "timed_out", "action_required"]),
        help="Comma-separated list of check conclusion values that should cause immediate exit (e.g. failure,cancelled)",
    )
    parser.add_argument(
        "--require-success",
        action="store_true",
        default=False,
        help="Only consider success when all checks succeed",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.interval == 1 else logging.INFO)
    if args.fail_on:
        args.fail_on = [f.strip() for f in args.fail_on.split(",") if f.strip()]

    fail_fast = not args.no_fail_fast
    owner, repo_name = parse_repo(args.repo)

    tries = 0
    while tries < args.max_tries:
        tries += 1
        sha = get_pr_head_sha(owner, repo_name, args.pr)
        if not sha:
            logging.warning("Unable to determine PR head; will retry")
            time.sleep(args.interval)
            continue
        check_runs = get_check_runs(owner, repo_name, sha)
        if check_runs is None:
            logging.warning("Unable to retrieve check runs; will retry")
            time.sleep(args.interval)
            continue
        total, completed, success, details = summarize_check_runs(check_runs)
        logging.info(
            "PR %s @ %s: %s/%s completed, %s success",
            args.pr,
            sha[:7],
            completed,
            total,
            success,
        )

        # Print details if small
        if len(details) <= 40:
            for name, _status, conclusion in details:
                logging.info(
                    "  - %s: status=%s, conclusion=%s", name, _status, conclusion
                )

        # If fail-fast and any completed check has failure, stop
        if fail_fast:
            for name, _status, conclusion in details:
                if conclusion and conclusion.lower() in {
                    v.lower() for v in args.fail_on
                }:
                    logging.error("Fail-fast: check %s concluded %s", name, conclusion)
                    return 1

        # If all completed
        if completed == total and total > 0:
            if success == total:
                logging.info("All checks succeeded")
                return 0
            else:
                logging.error("All checks completed but not all successful")
                return 1 if not args.require_success else 2

        # Not finished; sleep then next try
        time.sleep(args.interval)

    logging.error(
        "Timeout after %s attempts (%ss interval)", args.max_tries, args.interval
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
