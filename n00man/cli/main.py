#!/usr/bin/env python3
"""Lightweight CLI for the n00man agent foundry."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def scaffold_agent(name: str, role: str) -> None:
    """Delegate to the existing scaffold shell helper to create a new agent stub."""
    script = ROOT / "scripts" / "scaffold-agent.sh"
    if not script.exists():
        raise SystemExit(f"Missing scaffold script at {script}")
    subprocess.run([str(script), name, role], check=True)


def list_agents() -> int:
    """List registered agents under docs/agents with their README/profile hints."""
    agents_dir = ROOT / "docs" / "agents"
    if not agents_dir.exists():
        print(
            "[n00man] docs/agents directory not found (has scaffolding been initialised?)"
        )
        return 1

    agents = sorted(p for p in agents_dir.iterdir() if p.is_dir())
    if not agents:
        print(
            "[n00man] No agents registered yet. Use `n00man scaffold --name ... --role ...`."
        )
        return 0

    for agent in agents:
        profile = agent / "agent-profile.adoc"
        status = "✓" if profile.exists() else "∅"
        print(f"{agent.name}\t{status}\t{profile.relative_to(ROOT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    scaffold = subparsers.add_parser(
        "scaffold", help="Create a new agent profile (wraps scripts/scaffold-agent.sh)"
    )
    scaffold.add_argument(
        "--name", required=True, help="Agent slug (used for directory name)"
    )
    scaffold.add_argument("--role", required=True, help="Agent primary role/title")

    subparsers.add_parser("list", help="List agents under docs/agents")

    args = parser.parse_args(argv)

    if args.command == "scaffold":
        scaffold_agent(args.name, args.role)
        return 0
    if args.command == "list":
        return list_agents()

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
