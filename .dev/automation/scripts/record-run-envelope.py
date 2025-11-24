#!/usr/bin/env python3
"""Append a run envelope entry for automation scripts.

Usage:
  record-run-envelope.py --capability workspace.metaCheck --status success --asset artifacts/path.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_ROOT = WORKSPACE_ROOT / ".dev" / "automation" / "artifacts" / "automation"
RUN_LOG = ARTIFACTS_ROOT / "run-envelopes.jsonl"


def slugify(value: str) -> str:
    lowered = value.lower()
    cleaned: list[str] = []
    for ch in lowered:
        if ch.isalnum() or ch in {".", "_", "-"}:
            cleaned.append(ch)
        else:
            cleaned.append("-")
    slug = "".join(cleaned)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def iso_compact(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ").lower()


def build_envelope(
    capability_id: str,
    status: str,
    asset_ids: Iterable[str],
    dataset_id: str | None,
    notes: str | None,
) -> dict:
    started = datetime.now(timezone.utc)
    run_id = f"run.{slugify(capability_id)}.{iso_compact(started)}"
    return {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "capability_id": capability_id,
        "status": status,
        "started_at": started.isoformat(),
        "completed_at": started.isoformat(),
        "duration_ms": 0,
        "asset_ids": [slugify(a) for a in asset_ids if a],
        "dataset_id": dataset_id,
        "telemetry_path": str(RUN_LOG.relative_to(WORKSPACE_ROOT)),
        "tags": ["automation"],
        "notes": notes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record a run envelope for automation telemetry."
    )
    parser.add_argument(
        "--capability",
        required=True,
        help="Capability identifier (e.g., workspace.metaCheck).",
    )
    parser.add_argument(
        "--status",
        default="success",
        help="Run status (success|failure|timeout|skipped|cancelled).",
    )
    parser.add_argument(
        "--asset", action="append", default=[], help="Asset IDs or filenames produced."
    )
    parser.add_argument("--dataset", help="Dataset identifier when applicable.")
    parser.add_argument("--notes", help="Optional notes for the run.")
    args = parser.parse_args()

    envelope = build_envelope(
        capability_id=args.capability,
        status=args.status,
        asset_ids=args.asset,
        dataset_id=args.dataset,
        notes=args.notes,
    )

    ARTIFACTS_ROOT.mkdir(parents=True, exist_ok=True)
    with RUN_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(envelope) + "\n")

    print(
        f"[run-envelope] recorded {envelope['run_id']} -> {envelope['telemetry_path']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
