#!/usr/bin/env python3
# pylint: disable=missing-function-docstring,line-too-long,invalid-name
"""Generate the Control Panel Markdown linking radar, runbooks, and preflight artefacts."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, cast

from lib import project_metadata


def relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def load_radar(radar_path: Path) -> Dict[str, object]:
    if not radar_path.exists():
        return {}
    return json.loads(radar_path.read_text(encoding="utf-8"))


def collect_preflight(artifact_dir: Path) -> List[Dict[str, object]]:
    if not artifact_dir.exists():
        return []
    entries: Dict[str, Dict[str, Any]] = {}
    for artifact in sorted(artifact_dir.glob("*-preflight.json")):
        try:
            payload = json.loads(artifact.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        identifier = payload.get("id") or artifact.stem.split("-")[0]
        mtime = artifact.stat().st_mtime
        existing = entries.get(identifier)
        existing_mtime = (
            float(existing.get("mtime", -1.0)) if isinstance(existing, dict) else -1.0
        )
        if not existing or mtime > existing_mtime:
            payload["artifactPath"] = str(artifact)
            entries[identifier] = {"payload": payload, "mtime": mtime}
    ordered = sorted(
        entries.values(),
        key=lambda item: str(item.get("payload", {}).get("status", "zzz")),
    )
    return [entry["payload"] for entry in ordered]


def collect_jobs(jobs_root: Path, org_root: Path) -> List[Dict[str, object]]:
    if not jobs_root.exists():
        return []
    cortex_root = org_root / "n00tropic-cerebrum" / "n00-cortex"
    schema = cortex_root / "schemas" / "project-metadata.schema.json"
    taxonomy = cortex_root / "data" / "catalog" / "project-tags.yaml"
    validator = project_metadata.load_schema(schema)
    canonical_tags, alias_map = project_metadata.load_tag_taxonomy(taxonomy)
    jobs: List[Dict[str, object]] = []
    for readme in sorted(jobs_root.glob("*/README.md")):
        try:
            document = project_metadata.extract_metadata(readme)
        except project_metadata.MetadataLoadError:
            continue
        errors, _, payload = project_metadata.validate_document(
            document, validator, canonical_tags, alias_map
        )
        if errors:
            continue
        jobs.append(
            {
                "id": payload.get("id"),
                "title": payload.get("title"),
                "status": payload.get("status"),
                "owner": payload.get("owner"),
                "review_date": payload.get("review_date"),
                "path": relative(readme, org_root),
            }
        )
    return jobs


def render_radar_section(radar: Dict[str, object]) -> str:
    if not radar:
        return "Lifecycle radar artefact not found. Run `project-lifecycle-radar.sh` first."
    lines = []
    lines.append(
        f"Generated: {radar.get('generatedAt', 'unknown')} | Documents scanned: {radar.get('documents', 0)}"
    )
    lifecycle_totals = cast(Dict[str, int], radar.get("lifecycleTotals", {}) or {})
    if lifecycle_totals:
        header = "| Lifecycle | Count |\n| --- | --- |"
        rows = [
            f"| {stage.title()} | {count} |"
            for stage, count in sorted(lifecycle_totals.items())
        ]
        lines.append("\n".join([header] + rows))
    buckets = cast(Dict[str, List[object]], radar.get("reviewBuckets", {}) or {})
    if buckets:
        lines.append("**Review Buckets**")
        for bucket in ("missing", "overdue", "due_7_days", "due_30_days"):
            items = buckets.get(bucket, []) or []
            if not items:
                continue
            lines.append(f"- {bucket.replace('_', ' ').title()}: {len(items)}")
    gaps_obj = radar.get("integrationGaps") or []
    gaps = gaps_obj if isinstance(gaps_obj, list) else []
    if gaps:
        grouped: Dict[str, List[str]] = defaultdict(list)
        for item in gaps:
            grouped[item.get("id", "unknown")].append(item.get("field", "field"))
        lines.append("**Integration Gaps**")
        for identifier, fields in grouped.items():
            field_list = ", ".join(sorted(set(fields)))
            lines.append(f"- `{identifier}` missing {field_list}")
    return "\n\n".join(lines)


def render_preflight_section(
    preflights: List[Dict[str, object]], org_root: Path
) -> str:
    if not preflights:
        return (
            "No preflight artefacts found. Run `project-preflight.sh` for active jobs."
        )
    header = "| ID | Status | Issues | Artefact |\n| --- | --- | --- | --- |"
    rows = []
    for payload in preflights:
        issues_list = (
            payload.get("preflightIssues") or payload.get("downstreamImpacts") or []
        )
        if not isinstance(issues_list, list):
            issues_list = []
        issue_text = "<br>".join(issues_list[:3]) + (
            "<br>…" if len(issues_list) > 3 else ""
        )
        rows.append(
            "| `{id}` | {status} | {issues} | {artifact} |".format(
                id=payload.get("id", "unknown"),
                status=payload.get("status", "?"),
                issues=issue_text or "—",
                artifact=relative(Path(str(payload.get("artifactPath", ""))), org_root),
            )
        )
    return "\n".join([header] + rows)


def render_jobs_section(jobs: List[Dict[str, object]]) -> str:
    if not jobs:
        return "No jobs found under `n00-horizons/jobs/`."
    header = "| ID | Title | Owner | Status | Review Date | Doc |\n| --- | --- | --- | --- | --- | --- |"
    rows = []
    for job in jobs:
        rows.append(
            "| `{id}` | {title} | {owner} | {status} | {review} | {path} |".format(
                id=job.get("id"),
                title=job.get("title", "—"),
                owner=job.get("owner", "—"),
                status=job.get("status", "—"),
                review=job.get("review_date", "—"),
                path=job.get("path", ""),
            )
        )
    return "\n".join([header] + rows)


def main() -> int:
    _, workspace_root, org_root = project_metadata.resolve_roots()
    radar_path = (
        org_root
        / ".dev"
        / "automation"
        / "artifacts"
        / "project-sync"
        / "lifecycle-radar.json"
    )
    preflight_dir = org_root / ".dev" / "automation" / "artifacts" / "project-sync"
    jobs_root = workspace_root / "n00-horizons" / "jobs"

    radar = load_radar(radar_path)
    preflights = collect_preflight(preflight_dir)
    jobs = collect_jobs(jobs_root, org_root)

    control_panel_path = workspace_root / "n00-horizons" / "docs" / "control-panel.md"
    generated_at = datetime.now(timezone.utc).strftime("%d-%m-%YT%H:%M:%SZ")

    content = f"""# Control Panel – Readiness & Lifecycle Snapshot

Generated: {generated_at}

## Quick Links

- [Project Orchestration Runbook](../n00t/START HERE/PROJECT_ORCHESTRATION.md)
- [Task Slice Playbook](task-slice-playbook.md)
- [Job Pipeline](job-pipeline.md)
- Radar JSON: `{relative(radar_path, org_root)}`

## Lifecycle Radar

{render_radar_section(radar)}

## Preflight Watchlist

{render_preflight_section(preflights, org_root)}

## Outstanding Jobs

{render_jobs_section([job for job in jobs if str(job.get('status','')).lower() not in {'done','archived'}])}

## How to Rebuild

```bash
.dev/automation/scripts/project-lifecycle-radar.sh
.dev/automation/scripts/project-preflight.sh --path <doc>
.dev/automation/scripts/project-control-panel.sh
```
"""
    control_panel_path.write_text(content.strip() + "\n", encoding="utf-8")
    print(json.dumps({"path": str(control_panel_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
