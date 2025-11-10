#!/usr/bin/env python3
"""Helper CLI for the n00-dashboard Swift workspace."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def build(args: argparse.Namespace) -> None:
    cmd = ["swift", "build"]
    if args.tests:
        cmd.append("--build-tests")
    run(cmd)


def test() -> None:
    run(["swift", "test"])


def status() -> None:
    run(["git", "status", "-sb"])


def main() -> int:
    parser = argparse.ArgumentParser(description="n00-dashboard helper CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Run swift build for the dashboard.")
    build_parser.add_argument("--tests", action="store_true", help="Also build tests.")

    subparsers.add_parser("test", help="Execute the swift test suite.")
    subparsers.add_parser("status", help="Show git status for the dashboard repo.")

    args = parser.parse_args()
    if args.command == "build":
        build(args)
    elif args.command == "test":
        test()
    elif args.command == "status":
        status()
    else:  # pragma: no cover
        parser.print_help()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
