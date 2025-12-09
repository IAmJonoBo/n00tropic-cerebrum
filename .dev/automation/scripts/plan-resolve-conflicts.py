#!/usr/bin/env python3
"""Helper that fails fast when planner conflicts remain unresolved."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_conflicts(args: argparse.Namespace) -> list[dict]:
    if args.telemetry:
        payload = json.loads(Path(args.telemetry).read_text(encoding="utf-8"))
        return payload.get("conflicts", [])
    if args.plan:
        text = Path(args.plan).read_text(encoding="utf-8")
        conflicts: list[dict] = []
        for line in text.splitlines():
            if "[[RESOLVE]]" in line:
                conflicts.append({"description": line.strip()})
        return conflicts
    raise SystemExit("Provide --telemetry or --plan")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check planner conflicts")
    parser.add_argument("--telemetry", help="Planner telemetry JSON path")
    parser.add_argument("--plan", help="Plan markdown path")
    parser.add_argument("--allow", type=int, default=0)
    args = parser.parse_args()
    conflicts = load_conflicts(args)
    unresolved = [c for c in conflicts if not c.get("resolution")]
    if len(unresolved) > args.allow:
        raise SystemExit(
            f"Found {len(unresolved)} unresolved conflicts (allowed {args.allow})."
        )
    print(json.dumps({"status": "ok", "conflicts": len(unresolved)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
