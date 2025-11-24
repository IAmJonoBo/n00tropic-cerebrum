#!/usr/bin/env python3
"""Generate a lifecycle readiness radar from metadata-bearing artefacts."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lib import project_metadata


def parse_review_date(value: object) -> Optional[date]:
    if not isinstance(value, str):
        return None
    for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def default_documents() -> List[Path]:
    _, workspace_root, org_root = project_metadata.resolve_roots()
    documents: List[Path] = []
    documents.extend(
        project_metadata.discover_documents(
            workspace_root / "n00-horizons" / "ideas", ["README.md"]
        )
    )
    documents.extend(
        project_metadata.discover_documents(
            workspace_root / "n00-horizons" / "learning-log",
            ["LL-*.md"],
            recursive=False,
        )
    )
    documents.extend(
        project_metadata.discover_documents(
            org_root / "n00tropic_HQ" / "98. Internal-Projects", ["*.md"]
        )
    )
    return sorted(set(documents))


def infer_slice_type(path: Path) -> str:
    parts = [p.lower() for p in path.parts]
    if "ideas" in parts:
        return "idea"
    if "learning-log" in parts:
        return "learning-log"
    if "internal-projects" in " ".join(parts):
        return "project"
    if "observability" in parts:
        return "instrumentation"
    return "artifact"


def relative_to_org(path: Path, org_root: Path) -> str:
    try:
        return str(path.relative_to(org_root))
    except ValueError:
        return str(path)


def load_documents(paths: List[Path]) -> Tuple[List[Dict[str, object]], Path]:
    _, workspace_root, org_root = project_metadata.resolve_roots()
    schema_path = (
        workspace_root / "n00-cortex" / "schemas" / "project-metadata.schema.json"
    )
    taxonomy_path = (
        workspace_root / "n00-cortex" / "data" / "catalog" / "project-tags.yaml"
    )

    validator = project_metadata.load_schema(schema_path)
    canonical_tags, alias_map = project_metadata.load_tag_taxonomy(taxonomy_path)

    entries: List[Dict[str, object]] = []
    for path in paths:
        resolved = path.resolve()
        try:
            document = project_metadata.extract_metadata(resolved)
        except project_metadata.MetadataLoadError as exc:
            entries.append(
                {
                    "id": resolved.stem,
                    "path": relative_to_org(resolved, org_root),
                    "slice": infer_slice_type(resolved),
                    "metadata": {},
                    "errors": [str(exc)],
                    "warnings": [],
                }
            )
            continue

        errors, warnings, payload = project_metadata.validate_document(
            document, validator, canonical_tags, alias_map
        )
        errors.extend(project_metadata.ensure_paths_exist(document))
        entries.append(
            {
                "id": payload.get("id") or resolved.stem,
                "path": relative_to_org(resolved, org_root),
                "slice": infer_slice_type(resolved),
                "metadata": payload,
                "errors": errors,
                "warnings": warnings,
            }
        )

    return entries, org_root


def bucket_review(
    entry: Dict[str, object], today: date
) -> Tuple[str, Dict[str, object]]:
    metadata = entry.get("metadata", {})
    review_raw = metadata.get("review_date") if isinstance(metadata, dict) else None
    item = {
        "id": entry.get("id"),
        "path": entry.get("path"),
        "review_date": review_raw,
    }
    if not review_raw:
        return "missing", item
    review_dt = parse_review_date(review_raw)
    if not review_dt:
        return "missing", item

    if review_dt < today:
        return "overdue", item
    if review_dt <= today + timedelta(days=7):
        return "due_7_days", item
    if review_dt <= today + timedelta(days=30):
        return "due_30_days", item
    return "healthy", item


def build_radar(entries: List[Dict[str, object]]) -> Dict[str, object]:
    today = date.today()
    lifecycle_totals: Dict[str, int] = {}
    status_totals: Dict[str, int] = {}
    review_buckets = {
        "missing": [],
        "overdue": [],
        "due_7_days": [],
        "due_30_days": [],
        "healthy": [],
    }
    link_gaps: List[Dict[str, object]] = []
    integration_gaps: List[Dict[str, object]] = []
    metadata_errors: List[Dict[str, object]] = []

    for entry in entries:
        metadata = entry.get("metadata") or {}
        if entry.get("errors"):
            for err in entry["errors"]:
                metadata_errors.append(
                    {
                        "id": entry.get("id"),
                        "path": entry.get("path"),
                        "message": err,
                    }
                )

        lifecycle = str(metadata.get("lifecycle_stage") or "unknown").lower()
        lifecycle_totals[lifecycle] = lifecycle_totals.get(lifecycle, 0) + 1

        status = str(metadata.get("status") or "unknown").lower()
        status_totals[status] = status_totals.get(status, 0) + 1

        bucket, payload = bucket_review(entry, today)
        review_buckets[bucket].append(payload)

        links = metadata.get("links") or []
        if not links:
            link_gaps.append(
                {
                    "id": entry.get("id"),
                    "path": entry.get("path"),
                    "reason": "links[] missing",
                }
            )

        lifecycle_requires_integrations = lifecycle == "deliver" or str(
            entry.get("id") or ""
        ).startswith("job-")
        if lifecycle_requires_integrations:
            if not metadata.get("github_project"):
                integration_gaps.append(
                    {
                        "id": entry.get("id"),
                        "path": entry.get("path"),
                        "field": "github_project",
                    }
                )
            if not metadata.get("erpnext_project"):
                integration_gaps.append(
                    {
                        "id": entry.get("id"),
                        "path": entry.get("path"),
                        "field": "erpnext_project",
                    }
                )

    status = (
        "attention"
        if any(
            [
                metadata_errors,
                integration_gaps,
                link_gaps,
                review_buckets["missing"],
                review_buckets["overdue"],
            ]
        )
        else "ok"
    )

    return {
        "status": status,
        "generatedAt": datetime.now(timezone.utc).strftime("%d-%m-%YT%H:%M:%SZ"),
        "documents": len(entries),
        "lifecycleTotals": lifecycle_totals,
        "statusTotals": status_totals,
        "reviewBuckets": review_buckets,
        "linkGaps": link_gaps,
        "integrationGaps": integration_gaps,
        "metadataErrors": metadata_errors,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths", nargs="*", type=Path, help="Optional explicit documents to analyse."
    )
    parser.add_argument(
        "--json",
        type=Path,
        help="Optional report output path (defaults to automation artifacts directory).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    documents = args.paths if args.paths else default_documents()
    entries, org_root = load_documents(documents)
    radar = build_radar(entries)

    report_path = (
        args.json
        if args.json
        else org_root
        / ".dev"
        / "automation"
        / "artifacts"
        / "project-sync"
        / "lifecycle-radar.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = dict(radar)
    report["reportPath"] = str(report_path)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
