#!/usr/bin/env python3
"""Validate all example agent briefs and write results to automation artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
BRIEFS_DIR = ROOT / "n00man" / "docs" / "briefs"
ARTIFACT_ROOT = ROOT / ".dev/automation/artifacts/n00man"

sys.path.insert(0, str(ROOT))

from n00man.core import (  # noqa: E402
    AgentGovernanceValidator,
    build_agent_profile,
)


def _load_briefs(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.json"))


def _build_profile(raw: dict[str, Any]):
    return build_agent_profile(
        agent_id=raw["agent_id"],
        name=raw.get("name", raw["agent_id"]),
        role=raw["role"],
        description=raw["description"],
        capabilities=raw.get("capabilities"),
        model_config=raw.get("model_config"),
        guardrails=raw.get("guardrails"),
        tags=raw.get("tags"),
        owner=raw.get("owner"),
        status=raw.get("status"),
        metadata=raw.get("metadata"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--briefs-dir",
        default=BRIEFS_DIR,
        help="Directory containing agent briefs (*.json)",
    )
    parser.add_argument(
        "--artifact-root",
        default=ARTIFACT_ROOT,
        help="Where to write JSON summaries",
    )
    args = parser.parse_args()

    briefs_dir = Path(args.briefs_dir).expanduser().resolve()
    artifact_root = Path(args.artifact_root).expanduser().resolve()
    artifact_root.mkdir(parents=True, exist_ok=True)

    briefs = _load_briefs(briefs_dir)
    if not briefs:
        raise SystemExit(f"No briefs found under {briefs_dir}")

    validator = AgentGovernanceValidator()
    results = []
    failures = 0
    for brief_path in briefs:
        data = json.loads(brief_path.read_text(encoding="utf-8"))
        profile = _build_profile(data)
        errors = validator.collect_errors(profile.to_dict())
        if errors:
            failures += 1
            results.append(
                {
                    "brief": str(brief_path),
                    "status": "failed",
                    "errors": errors,
                }
            )
        else:
            results.append({"brief": str(brief_path), "status": "passed"})

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    summary = {
        "timestamp": timestamp,
        "briefs_dir": str(briefs_dir),
        "results": results,
        "total": len(results),
        "failures": failures,
    }

    artifact_path = artifact_root / f"governance-sweep-{timestamp}.json"
    artifact_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps({"status": "success", "artifact": str(artifact_path)}, indent=2))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
