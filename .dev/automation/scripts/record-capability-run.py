#!/usr/bin/env python3
"""Append a structured capability run record for dashboard/agent telemetry."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORE = (
    ROOT / ".dev" / "automation" / "artifacts" / "automation" / "agent-runs.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--capability",
        required=True,
        help="Capability identifier (e.g. workspace.metaCheck).",
    )
    parser.add_argument(
        "--status",
        default="unknown",
        help="Run status (succeeded, failed, skipped, etc.).",
    )
    parser.add_argument("--summary", default="", help="Short human-readable summary.")
    parser.add_argument(
        "--log-path",
        dest="log_path",
        help="Optional log path relative to workspace root.",
    )
    parser.add_argument("--started", help="ISO8601 timestamp for when the run started.")
    parser.add_argument(
        "--completed", help="ISO8601 timestamp for when the run completed."
    )
    parser.add_argument(
        "--metadata",
        help="Optional JSON string containing additional metadata to persist with the run.",
    )
    parser.add_argument(
        "--store",
        default=str(DEFAULT_STORE),
        help=f"Override storage path (default: {DEFAULT_STORE}).",
    )
    return parser.parse_args()


def iso_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def load_store(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return data
    return []


def main() -> int:
    args = parse_args()
    max_entries = int(os.getenv("CAPABILITY_RUN_LIMIT", "200"))

    started = args.started or iso_now()
    completed = args.completed or started
    store_path = Path(args.store)

    metadata: Dict[str, Any] = {}
    if args.metadata:
        try:
            parsed = json.loads(args.metadata)
            if isinstance(parsed, dict):
                metadata = parsed
        except json.JSONDecodeError:
            metadata = {"raw": args.metadata}

    runs = load_store(store_path)
    entry: Dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "capability": args.capability,
        "status": args.status,
        "summary": args.summary,
        "started": started,
        "completed": completed,
    }
    if args.log_path:
        entry["logPath"] = args.log_path
    if metadata:
        entry["metadata"] = metadata

    runs.append(entry)
    if len(runs) > max_entries:
        runs = runs[-max_entries:]
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(json.dumps(runs, indent=2) + "\n", encoding="utf-8")
    print(f"[record-capability-run] Logged {args.capability} → {store_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
