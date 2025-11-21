#!/usr/bin/env python3
# pylint: disable=missing-function-docstring,line-too-long,invalid-name,too-many-lines
"""
Project orchestration utilities for n00t capabilities.

Supports metadata capture, GitHub synchronisation planning, and ERPNext planning.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple, cast
from urllib.parse import urlparse

try:
    import yaml  # type: ignore[import-untyped]  # pylint: disable=import-error
except ImportError:  # pragma: no cover - surfaced at runtime if missing
    yaml = None  # type: ignore[assignment]

from lib.project_metadata import (
    MetadataLoadError,
    ensure_paths_exist,
    extract_metadata,
    find_duplicate_ids,
    discover_documents,
    load_schema,
    load_tag_taxonomy,
    resolve_roots,
    validate_document,
    write_metadata,
)

TIMESTAMP_FMT = "%Y-%m-%dT%H:%M:%SZ"
DISPLAY_DATE_FMT = "%d-%m-%Y"


def now() -> str:
    return datetime.now(tz=timezone.utc).strftime(TIMESTAMP_FMT)


def format_calendar_date(value: date) -> str:
    return value.strftime(DISPLAY_DATE_FMT)


def emit_progress(stage: str, message: str, context: Optional[Dict[str, object]] = None) -> None:
    payload: Dict[str, object] = {
        "timestamp": now(),
        "stage": stage,
        "message": message,
    }
    if context:
        for key, value in context.items():
            if value is None:
                continue
            if isinstance(value, Path):
                payload[key] = str(value)
            else:
                payload[key] = value
    print(json.dumps(payload, sort_keys=True), file=sys.stderr)


def load_registry(registry_path: Path) -> Dict[str, object]:
    if registry_path.exists():
        return json.loads(registry_path.read_text(encoding="utf-8"))
    return {"version": "0.1.0", "last_updated": None, "projects": []}


def save_registry(registry_path: Path, registry: Dict[str, object]) -> None:
    registry["last_updated"] = now()
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def find_registry_entry(registry: Dict[str, object], project_id: str) -> Optional[Dict[str, object]]:
    projects = registry.get("projects", [])
    if not isinstance(projects, list):
        return None
    for entry in projects:
        if isinstance(entry, dict) and entry.get("id") == project_id:
            return entry
    return None


def upsert_registry_entry(
    registry: Dict[str, object], project_id: str, payload: Dict[str, object]
) -> Dict[str, object]:
    projects = registry.setdefault("projects", [])
    if not isinstance(projects, list):
        projects = []
        registry["projects"] = projects
    for index, entry in enumerate(projects):
        if isinstance(entry, dict) and entry.get("id") == project_id:
            merged = dict(entry)
            merged.update(payload)
            projects[index] = merged
            return merged
    projects.append(payload)
    return payload


def compute_drift(metadata: Dict[str, object], existing: Optional[Dict[str, object]]) -> List[str]:
    if not existing:
        return []
    drift: List[str] = []
    for key in ("lifecycle_stage", "status", "owner", "review_date"):
        new_value = metadata.get(key)
        if existing.get(key) != new_value:
            drift.append(f"{key} changed from '{existing.get(key)}' to '{new_value}'")
    return drift


def dedupe_list(values: Sequence[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def dedupe_paths(paths: Sequence[Path]) -> List[Path]:
    seen = set()
    ordered: List[Path] = []
    for value in paths:
        if not value:
            continue
        resolved = Path(value).resolve()
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(resolved)
    return ordered


def compute_impacts(metadata: Dict[str, object]) -> Tuple[List[str], List[str]]:
    upstream: List[str] = []
    downstream: List[str] = []
    links = metadata.get("links", [])
    if isinstance(links, list):
        for link in links:
            if not isinstance(link, dict):
                continue
            target_type = str(link.get("type", "")).lower()
            target_path = link.get("path")
            description = f"{target_type or 'link'} -> {target_path}"
            if target_type in {"idea", "research", "learning-log", "charter", "experiment", "project"}:
                upstream.append(description)
            elif target_type in {"adr", "runbook", "doc"}:
                upstream.append(description)
            else:
                downstream.append(description)
    if metadata.get("github_project") in {None, "null", ""}:
        downstream.append(
            "Create or reference a GitHub project board; coordinate with Delivery and log a TODO."
        )
    if metadata.get("erpnext_project") in {None, "null", ""}:
        downstream.append(
            "Provision ERPNext Project/Tasks and record identifiers in metadata; capture TODO in Platform Ops backlog."
        )
    return upstream, downstream


def parse_review_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def evaluate_preflight_requirements(metadata: Dict[str, object]) -> Tuple[List[str], List[str]]:
    issues: List[str] = []
    advisories: List[str] = []

    review_val = metadata.get("review_date")
    review_raw = review_val if isinstance(review_val, str) else None
    review_dt = parse_review_date(review_raw)
    if not review_raw:
        issues.append("review_date missing; set a review cadence before delivery work starts.")
    elif not review_dt:
        issues.append("review_date must use DD-MM-YYYY format; update the metadata block.")
    elif review_dt < date.today():
        issues.append(
            f"review_date {format_calendar_date(review_dt)} is in the past; extend or archive the artefact."
        )

    links = metadata.get("links") or []
    if not links:
        issues.append("links[] is empty; cite upstream/downstream slices for traceability.")

    lifecycle = str(metadata.get("lifecycle_stage") or "").lower()
    identifier = str(metadata.get("id") or "")
    requires_integrations = identifier.startswith("job-") or lifecycle == "deliver"

    github_project = metadata.get("github_project")
    erpnext_project = metadata.get("erpnext_project")

    if requires_integrations:
        if not github_project:
            issues.append("github_project missing for delivery-stage work; set the Project board URL.")
        if not erpnext_project:
            issues.append("erpnext_project missing for delivery-stage work; provide the ERPNext Project code.")
    else:
        if not github_project:
            advisories.append("github_project not set (optional for non-delivery slices).")
        if not erpnext_project:
            advisories.append("erpnext_project not set (optional for non-delivery slices).")

    return issues, advisories


def validate_metadata_document(path: Path):
    _, workspace_root, _ = resolve_roots()
    schema_path = workspace_root / "n00-cortex" / "schemas" / "project-metadata.schema.json"
    taxonomy_path = workspace_root / "n00-cortex" / "data" / "catalog" / "project-tags.yaml"
    validator = load_schema(schema_path)
    canonical_tags, alias_map = load_tag_taxonomy(taxonomy_path)

    document = extract_metadata(path)
    errors, warnings, payload = validate_document(document, validator, canonical_tags, alias_map)
    errors.extend(ensure_paths_exist(document))
    if errors:
        raise RuntimeError("\n".join(errors))
    return document, payload, warnings


def discover_workspace_metadata() -> List[Path]:
    """Discover known metadata-bearing documents across Horizons and HQ."""
    _, workspace_root, org_root = resolve_roots()
    documents: Set[Path] = set()
    documents.update(discover_documents(workspace_root / "n00-horizons" / "ideas", ["README.md"]))
    documents.update(discover_documents(workspace_root / "n00-horizons" / "jobs", ["README.md"]))
    documents.update(
        discover_documents(
            workspace_root / "n00-horizons" / "learning-log", ["LL-*.md"], recursive=False
        )
    )
    documents.update(discover_documents(org_root / "n00tropic_HQ" / "98. Internal-Projects", ["*.md"]))
    return sorted(documents)


def summarise_result(
    action: str,
    document_path: Path,
    metadata: Dict[str, object],
    upstream: List[str],
    downstream: List[str],
    drift: List[str],
    warnings: List[str],
    status_override: Optional[str] = None,
) -> Dict[str, object]:
    status = status_override or ("attention" if drift else "ok")
    return {
        "action": action,
        "id": metadata.get("id"),
        "title": metadata.get("title"),
        "status": status,
        "metadataPath": str(document_path),
        "upstreamImpacts": upstream,
        "downstreamImpacts": downstream,
        "drift": drift,
        "warnings": warnings,
    }


def validate_github_reference(url: Optional[str]) -> Optional[str]:
    if not url or url in {"null", ""}:
        return "github_project metadata is empty"
    parsed = urlparse(url)
    if parsed.scheme not in {"https"} or "github.com" not in parsed.netloc:
        return "github_project must be an https://github.com/orgs/... project URL"
    if "/projects/" not in parsed.path:
        return "github_project URL should reference a GitHub Project board"
    return None


def validate_erpnext_reference(code: Optional[str]) -> Optional[str]:
    if not code or code in {"null", ""}:
        return "erpnext_project metadata is empty"
    if not code.upper().startswith("PM-"):
        return "erpnext_project should follow the PM- prefix convention"
    return None


def capture(path: Path, registry_path: Path) -> Dict[str, object]:
    emit_progress("capture.start", "Validating metadata document", {"path": path})
    document, payload, warnings = validate_metadata_document(path)
    emit_progress(
        "capture.metadata",
        "Metadata validation complete",
        {"id": payload.get("id"), "path": path},
    )
    original_tags = document.payload.get("tags")
    normalised_tags = payload.get("tags")
    if isinstance(original_tags, list) and normalised_tags and original_tags != normalised_tags:
        updated_payload = dict(document.payload)
        updated_payload["tags"] = normalised_tags
        write_metadata(document, updated_payload)
        document = extract_metadata(path)
        payload = dict(updated_payload)
        warnings.append("normalised tag aliases to canonical taxonomy entries")
        emit_progress(
            "capture.tags",
            "Normalised tags to canonical taxonomy entries",
            {"id": payload.get("id"), "path": path},
        )

    registry = load_registry(registry_path)
    emit_progress(
        "capture.registry",
        "Loaded project registry",
        {"id": payload.get("id"), "registryPath": registry_path},
    )
    existing = find_registry_entry(registry, payload["id"])
    drift = compute_drift(payload, existing)
    upstream, downstream = compute_impacts(payload)

    entry_payload = dict(payload)
    entry_payload.update(
        {
            "id": payload["id"],
            "source_path": str(path),
            "last_captured": now(),
            "tags": payload.get("tags", []),
        }
    )
    upsert_registry_entry(registry, payload["id"], entry_payload)
    save_registry(registry_path, registry)
    emit_progress(
        "capture.registry",
        "Persisted project registry entry",
        {"id": payload.get("id"), "registryPath": registry_path},
    )

    result = summarise_result(
        action="capture",
        document_path=path,
        metadata=payload,
        upstream=upstream,
        downstream=downstream,
        drift=drift,
        warnings=warnings,
    )
    result["registryPath"] = str(registry_path)
    emit_progress(
        "capture.complete",
        "Capture process complete",
        {"id": result.get("id"), "status": result.get("status")},
    )
    return result


def sync_github(path: Path, registry_path: Path) -> Dict[str, object]:
    emit_progress("sync.github.start", "Validating metadata document", {"path": path})
    _document, payload, warnings = validate_metadata_document(path)
    emit_progress(
        "sync.github.metadata",
        "Metadata validation complete",
        {"id": payload.get("id"), "path": path},
    )
    registry = load_registry(registry_path)
    emit_progress(
        "sync.github.registry",
        "Loaded project registry",
        {"id": payload.get("id"), "registryPath": registry_path},
    )
    existing = find_registry_entry(registry, payload["id"])
    drift = compute_drift(payload, existing)
    upstream, downstream = compute_impacts(payload)

    outcome = validate_github_reference(payload.get("github_project"))
    if outcome:
        downstream.append(outcome)
        emit_progress(
            "sync.github.validation",
            "GitHub reference requires attention",
            {"id": payload.get("id"), "message": outcome},
        )

    entry_payload = dict(existing or {})
    entry_payload.update(
        {
            "id": payload["id"],
            "last_github_sync": now(),
            "github_project": payload.get("github_project"),
        }
    )
    upsert_registry_entry(registry, payload["id"], entry_payload)
    save_registry(registry_path, registry)
    emit_progress(
        "sync.github.registry",
        "Persisted GitHub sync details",
        {"id": payload.get("id"), "registryPath": registry_path},
    )

    result = summarise_result(
        action="sync.github",
        document_path=path,
        metadata=payload,
        upstream=upstream,
        downstream=downstream,
        drift=drift,
        warnings=warnings,
        status_override="attention" if outcome else None,
    )
    result["registryPath"] = str(registry_path)
    emit_progress(
        "sync.github.complete",
        "GitHub sync planning complete",
        {"id": result.get("id"), "status": result.get("status")},
    )
    return result


def sync_erpnext(path: Path, registry_path: Path) -> Dict[str, object]:
    emit_progress("sync.erpnext.start", "Validating metadata document", {"path": path})
    _document, payload, warnings = validate_metadata_document(path)
    emit_progress(
        "sync.erpnext.metadata",
        "Metadata validation complete",
        {"id": payload.get("id"), "path": path},
    )
    registry = load_registry(registry_path)
    emit_progress(
        "sync.erpnext.registry",
        "Loaded project registry",
        {"id": payload.get("id"), "registryPath": registry_path},
    )
    existing = find_registry_entry(registry, payload["id"])
    drift = compute_drift(payload, existing)
    upstream, downstream = compute_impacts(payload)

    outcome = validate_erpnext_reference(payload.get("erpnext_project"))
    if outcome:
        downstream.append(outcome)
        emit_progress(
            "sync.erpnext.validation",
            "ERPNext reference requires attention",
            {"id": payload.get("id"), "message": outcome},
        )

    entry_payload = dict(existing or {})
    entry_payload.update(
        {
            "id": payload["id"],
            "last_erpnext_sync": now(),
            "erpnext_project": payload.get("erpnext_project"),
        }
    )
    upsert_registry_entry(registry, payload["id"], entry_payload)
    save_registry(registry_path, registry)
    emit_progress(
        "sync.erpnext.registry",
        "Persisted ERPNext sync details",
        {"id": payload.get("id"), "registryPath": registry_path},
    )

    result = summarise_result(
        action="sync.erpnext",
        document_path=path,
        metadata=payload,
        upstream=upstream,
        downstream=downstream,
        drift=drift,
        warnings=warnings,
        status_override="attention" if outcome else None,
    )
    result["registryPath"] = str(registry_path)
    emit_progress(
        "sync.erpnext.complete",
        "ERPNext sync planning complete",
        {"id": result.get("id"), "status": result.get("status")},
    )
    return result


def yaml_dump(data: Mapping[str, Any]) -> str:
    if yaml is None:
        raise RuntimeError("PyYAML is required. Install with `pip install pyyaml`." )
    return yaml.safe_dump(data, sort_keys=False).strip()


def slugify(value: str) -> str:
    slug = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "item"


def ensure_unique_path(base_dir: Path, slug: str) -> Tuple[Path, str]:
    candidate = slug
    counter = 1
    while (base_dir / candidate).exists():
        counter += 1
        candidate = f"{slug}-{counter}"
    return base_dir / candidate, candidate


def record_idea(
    registry_path: Path,
    title: str,
    owner: str,
    tags: List[str],
    sponsors: List[str],
    source: str,
    review_days: int,
) -> Dict[str, object]:
    emit_progress("record.idea.start", "Scaffolding idea document", {"title": title})
    _, workspace_root, _ = resolve_roots()
    ideas_root = workspace_root / "n00-horizons" / "ideas"
    ideas_root.mkdir(parents=True, exist_ok=True)

    slug = slugify(title)
    identifier = f"idea-{slug}"
    directory_path, identifier = ensure_unique_path(ideas_root, identifier)
    directory_path.mkdir(parents=True, exist_ok=True)

    review_date = format_calendar_date(
        (datetime.now(timezone.utc) + timedelta(days=review_days)).date()
    )
    tag_set = list(dict.fromkeys((tags or []) + ["knowledge/idea"]))

    metadata = {
        "id": identifier,
        "title": title,
        "lifecycle_stage": "discover",
        "status": "proposed",
        "owner": owner,
        "sponsors": sponsors or [],
        "source": source or "internal",
        "tags": tag_set or ["governance/project-management"],
        "review_date": review_date,
        "erpnext_project": None,
        "github_project": None,
        "links": [],
        "created": format_calendar_date(datetime.now(timezone.utc).date()),
    }

    body = textwrap.dedent(
        f"""---
{yaml_dump(metadata)}
---

# Idea: {title}

## Problem Statement

Describe the customer, operational, or technical challenge prompting this idea.

## Hypothesis

Summarise the expected outcome if the idea is implemented.

## Proposed Next Steps

1. Validate scope with stakeholders.
2. Identify upstream/downstream systems.
3. Prepare decision record and pilot plan.

## Open Questions

- What downstream repositories or teams must be informed?
- Are there policy or compliance constraints to surface?
- What evidence is required to promote this idea to a project?
"""
    ).strip()

    readme_path = directory_path / "README.md"
    readme_path.write_text(body + "\n", encoding="utf-8")
    emit_progress(
        "record.idea.document",
        "Idea scaffold written",
        {"path": readme_path, "id": identifier},
    )

    capture_result = capture(readme_path, registry_path)
    capture_result["created"] = str(readme_path)
    capture_result["note"] = "Idea scaffolded and registered."
    emit_progress(
        "record.idea.complete",
        "Idea registration complete",
        {"id": capture_result.get("id"), "status": capture_result.get("status")},
    )
    return capture_result


def record_job(
    registry_path: Path,
    title: str,
    owner: str,
    tags: List[str],
    sponsors: List[str],
    source: str,
    review_days: int,
    review_date_override: Optional[str],
    status: str,
    lifecycle: str,
    erpnext_project: Optional[str],
    github_project: Optional[str],
    links: List[str],
) -> Dict[str, object]:
    emit_progress("record.job.start", "Scaffolding job document", {"title": title})
    _, workspace_root, _ = resolve_roots()
    jobs_root = workspace_root / "n00-horizons" / "jobs"
    jobs_root.mkdir(parents=True, exist_ok=True)

    slug = slugify(title)
    identifier = f"job-{slug}"
    directory_path, identifier = ensure_unique_path(jobs_root, identifier)
    directory_path.mkdir(parents=True, exist_ok=True)

    review_date = review_date_override or format_calendar_date(
        (
            datetime.now(timezone.utc) + timedelta(days=review_days)
            if review_days > 0
            else datetime.now(timezone.utc)
        ).date()
    )
    tag_set = list(dict.fromkeys((tags or []) + ["delivery/job", "governance/project-management"]))

    metadata = {
        "id": identifier,
        "title": title,
        "lifecycle_stage": lifecycle or "deliver",
        "status": status or "queued",
        "owner": owner,
        "sponsors": sponsors or [],
        "source": source or "internal",
        "tags": tag_set,
        "review_date": review_date,
        "erpnext_project": erpnext_project,
        "github_project": github_project,
        "links": [parse_link_spec(link) for link in links if link] or [],
    }

    body = textwrap.dedent(
        f"""---
{yaml_dump(metadata)}
---

# Job: {title}

## Objective

Summarise the measurable outcome for this job and its success predicates.

## Inputs & Dependencies

- Reference upstream artefacts in `links` and note any blocking systems.

## Quality Gates

1. Define the frontier-standard validations, CI jobs, or reviews required before completion.
2. Capture telemetry or evidence expectations (logs, dashboards, ERPNext updates).

## Traceability & Telemetry

- Document how this job updates GitHub/ERPNext and where run IDs or artefacts will be logged.

## Notes

- Record progress updates, owners, and handoffs here.
"""
    ).strip()

    readme_path = directory_path / "README.md"
    readme_path.write_text(body + "\n", encoding="utf-8")
    emit_progress(
        "record.job.document",
        "Job scaffold written",
        {"path": readme_path, "id": identifier},
    )

    capture_result = capture(readme_path, registry_path)
    capture_result["created"] = str(readme_path)
    capture_result["note"] = "Job scaffolded and registered."
    emit_progress(
        "record.job.complete",
        "Job registration complete",
        {"id": capture_result.get("id"), "status": capture_result.get("status")},
    )
    return capture_result


def detect_title(path: Path) -> Optional[str]:
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return None


def ingest_markdown(
    registry_path: Path,
    path: Path,
    kind: str,
    owner: Optional[str],
    tags: List[str],
    status: Optional[str],
    lifecycle: Optional[str],
    review_days: int,
    identifier: Optional[str],
    sponsors: List[str],
    source: Optional[str],
    erpnext_project: Optional[str],
    github_project: Optional[str],
) -> Dict[str, object]:
    emit_progress(
        "ingest.start",
        "Ingesting markdown document",
        {"path": path, "kind": kind},
    )
    resolved = path.resolve()
    if not resolved.exists():
        raise RuntimeError(f"Document not found: {resolved}")

    kind = kind or "idea"
    default_lifecycle = {
        "idea": "discover",
        "project": "shape",
        "learn": "discover",
        "issue": "deliver",
        "job": "deliver",
    }.get(kind, "deliver")
    default_status = {
        "idea": "proposed",
        "project": "in-definition",
        "learn": "recorded",
        "issue": "open",
        "job": "queued",
    }.get(kind, "draft")

    try:
        document = extract_metadata(resolved)
        payload = dict(document.payload)
        create_front_matter = False
    except MetadataLoadError:
        create_front_matter = True
        payload = {}

    review_date = (
        format_calendar_date((datetime.now(timezone.utc) + timedelta(days=review_days)).date())
        if review_days > 0
        else None
    )

    if create_front_matter:
        title = detect_title(resolved) or resolved.stem.replace("-", " ").title()
        slug = slugify(identifier or f"{kind}-{title}")
        default_tags = tags or ["governance/project-management"]
        if kind == "job" and "delivery/job" not in default_tags:
            default_tags.append("delivery/job")
        if kind == "idea" and "knowledge/idea" not in default_tags:
            default_tags.append("knowledge/idea")
        if kind == "learn" and "knowledge/learning-log" not in default_tags:
            default_tags.append("knowledge/learning-log")
        metadata = {
            "id": identifier or f"{kind}-{slug}",
            "title": title,
            "lifecycle_stage": lifecycle or default_lifecycle,
            "status": status or default_status,
            "owner": owner or "unassigned",
            "sponsors": sponsors or [],
            "source": source or "ingested",
            "tags": default_tags,
            "review_date": review_date or format_calendar_date(datetime.now(timezone.utc).date()),
            "erpnext_project": erpnext_project,
            "github_project": github_project,
            "links": [],
        }
        original = resolved.read_text(encoding="utf-8")
        resolved.write_text(f"---\n{yaml_dump(metadata)}\n---\n" + original, encoding="utf-8")
        emit_progress(
            "ingest.front_matter",
            "Inserted metadata front matter",
            {"path": resolved, "id": metadata.get("id")},
        )
    else:
        updated = False
        if tags:
            existing_tags_obj = payload.get("tags")
            existing_tags = (
                [t for t in existing_tags_obj if isinstance(t, str)]
                if isinstance(existing_tags_obj, list)
                else []
            )
            merged_tags = list(dict.fromkeys((tags or []) + existing_tags))
            if kind == "idea" and "knowledge/idea" not in merged_tags:
                merged_tags.append("knowledge/idea")
            if kind == "learn" and "knowledge/learning-log" not in merged_tags:
                merged_tags.append("knowledge/learning-log")
            if kind == "job" and "delivery/job" not in merged_tags:
                merged_tags.append("delivery/job")
            payload["tags"] = merged_tags
            updated = True
        if owner:
            payload["owner"] = owner
            updated = True
        if sponsors:
            payload["sponsors"] = sponsors
            updated = True
        if status:
            payload["status"] = status
            updated = True
        if lifecycle:
            payload["lifecycle_stage"] = lifecycle
            updated = True
        if source:
            payload["source"] = source
            updated = True
        if erpnext_project is not None:
            payload["erpnext_project"] = erpnext_project
            updated = True
        if github_project is not None:
            payload["github_project"] = github_project
            updated = True
        if review_date and not payload.get("review_date"):
            payload["review_date"] = review_date
            updated = True
        if identifier:
            payload["id"] = identifier
            updated = True
        if kind == "idea":
            tags_field = cast(List[str], payload.get("tags") or [])
            if "knowledge/idea" not in tags_field:
                payload["tags"] = list(
                    dict.fromkeys(list(tags_field) + ["knowledge/idea"])  # type: ignore[arg-type]
                )
                updated = True
        if kind == "learn":
            tags_field = cast(List[str], payload.get("tags") or [])
            if "knowledge/learning-log" not in tags_field:
                payload["tags"] = list(
                    dict.fromkeys(list(tags_field) + ["knowledge/learning-log"])  # type: ignore[arg-type]
                )
                updated = True
        if kind == "job":
            tags_field = cast(List[str], payload.get("tags") or [])
            if "delivery/job" not in tags_field:
                payload["tags"] = list(
                    dict.fromkeys(list(tags_field) + ["delivery/job"])  # type: ignore[arg-type]
                )
                updated = True
        if updated:
            write_metadata(extract_metadata(resolved), payload)
            emit_progress(
                "ingest.update",
                "Updated metadata payload",
                {"path": resolved, "id": payload.get("id")},
            )

    capture_result = capture(resolved, registry_path)
    emit_progress(
        "ingest.complete",
        "Ingestion complete",
        {"id": capture_result.get("id"), "status": capture_result.get("status")},
    )
    return capture_result


def write_artifact(result: Dict[str, object]) -> None:
    _, _, org_root = resolve_roots()
    artifact_dir = org_root / ".dev" / "automation" / "artifacts" / "project-sync"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    action_str = str(result.get("action", "run"))
    artifact_path = artifact_dir / f"{result.get('id')}-{action_str.replace('.', '_')}.json"
    artifact_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["artifactPath"] = str(artifact_path)


def preflight(path: Path, registry_path: Path) -> Dict[str, object]:
    emit_progress("preflight.start", "Running project preflight", {"path": path})
    capture_result = capture(path, registry_path)
    write_artifact(capture_result)
    emit_progress(
        "preflight.stage",
        "Capture stage complete",
        {"id": capture_result.get("id"), "status": capture_result.get("status")},
    )

    emit_progress("preflight.stage", "Planning GitHub synchronisation", {"path": path})
    github_result = sync_github(path, registry_path)
    write_artifact(github_result)
    emit_progress(
        "preflight.stage",
        "GitHub synchronisation stage complete",
        {"id": github_result.get("id"), "status": github_result.get("status")},
    )

    emit_progress("preflight.stage", "Planning ERPNext synchronisation", {"path": path})
    erpnext_result = sync_erpnext(path, registry_path)
    write_artifact(erpnext_result)
    emit_progress(
        "preflight.stage",
        "ERPNext synchronisation stage complete",
        {"id": erpnext_result.get("id"), "status": erpnext_result.get("status")},
    )

    _, payload, _ = validate_metadata_document(path)
    issues, advisories = evaluate_preflight_requirements(payload)

    # Duplicate detection across workspace metadata
    try:
        documents = [extract_metadata(p) for p in discover_workspace_metadata()]
        duplicates = find_duplicate_ids(documents)
        if payload.get("id") in duplicates:
            dupe_paths = [
                str(doc.path) for doc in documents if (doc.payload.get("id") == payload.get("id"))
            ]
            issues.append(f"duplicate id '{payload.get('id')}' present in: {', '.join(dupe_paths)}")
    except Exception as exc:  # pragma: no cover - defensive
        advisories.append(f"duplicate detection skipped: {exc}")

    def _as_str_list(value: object) -> List[str]:
        if isinstance(value, list):
            return [v for v in value if isinstance(v, str)]
        return []

    combined_upstream = dedupe_list(
        _as_str_list(capture_result.get("upstreamImpacts"))
        + _as_str_list(github_result.get("upstreamImpacts"))
        + _as_str_list(erpnext_result.get("upstreamImpacts"))
    )
    combined_downstream = dedupe_list(
        _as_str_list(capture_result.get("downstreamImpacts"))
        + _as_str_list(github_result.get("downstreamImpacts"))
        + _as_str_list(erpnext_result.get("downstreamImpacts"))
        + issues
    )
    combined_warnings = dedupe_list(
        _as_str_list(capture_result.get("warnings"))
        + _as_str_list(github_result.get("warnings"))
        + _as_str_list(erpnext_result.get("warnings"))
        + advisories
    )
    combined_drift = dedupe_list(
        _as_str_list(capture_result.get("drift"))
        + _as_str_list(github_result.get("drift"))
        + _as_str_list(erpnext_result.get("drift"))
    )

    runs = [
        {
            "action": capture_result["action"],
            "status": capture_result["status"],
            "artifactPath": capture_result.get("artifactPath"),
        },
        {
            "action": github_result["action"],
            "status": github_result["status"],
            "artifactPath": github_result.get("artifactPath"),
        },
        {
            "action": erpnext_result["action"],
            "status": erpnext_result["status"],
            "artifactPath": erpnext_result.get("artifactPath"),
        },
    ]

    status = "attention" if issues or any(run["status"] != "ok" for run in runs) else "ok"

    result = {
        "action": "preflight",
        "id": payload.get("id"),
        "title": payload.get("title"),
        "status": status,
        "metadataPath": capture_result.get("metadataPath", str(path)),
        "upstreamImpacts": combined_upstream,
        "downstreamImpacts": combined_downstream,
        "drift": combined_drift,
        "warnings": combined_warnings,
        "preflightIssues": issues,
        "preflightAdvisories": advisories,
        "runs": runs,
    }
    emit_progress(
        "preflight.complete",
        "Preflight checks complete",
        {"id": result.get("id"), "status": result.get("status"), "issueCount": len(issues)},
    )
    return result


def registry_source_paths(registry: Dict[str, object]) -> List[Path]:
    sources: List[Path] = []
    projects_obj = registry.get("projects") or []
    if not isinstance(projects_obj, list):
        return sources
    for entry in projects_obj:
        if not isinstance(entry, dict):
            continue
        source_path = entry.get("source_path")
        if isinstance(source_path, str) and source_path.strip():
            sources.append(Path(source_path))
    return sources


def batch_preflight(paths: Sequence[Path], registry_path: Path) -> Dict[str, object]:
    deduped = dedupe_paths(paths)
    if not deduped:
        raise RuntimeError("No metadata paths resolved for batch preflight.")

    emit_progress(
        "batch.preflight.start",
        "Starting batch preflight run",
        {"documentCount": len(deduped), "registryPath": registry_path},
    )
    summary: List[Dict[str, object]] = []
    ok_count = 0
    attention_count = 0
    error_count = 0

    for path in deduped:
        emit_progress("batch.preflight.run", "Processing metadata document", {"path": path})
        if not path.exists():
            error_count += 1
            summary.append(
                {
                    "metadataPath": str(path),
                    "status": "error",
                    "error": "metadata document not found",
                }
            )
            emit_progress(
                "batch.preflight.error",
                "Metadata document not found",
                {"path": path},
            )
            continue

        try:
            run_result = preflight(path, registry_path)
            write_artifact(run_result)
            status = run_result.get("status", "attention")
            if status == "ok":
                ok_count += 1
            else:
                attention_count += 1
            summary.append(
                {
                    "metadataPath": run_result.get("metadataPath", str(path)),
                    "artifactPath": run_result.get("artifactPath"),
                    "status": status,
                    "id": run_result.get("id"),
                    "title": run_result.get("title"),
                }
            )
            emit_progress(
                "batch.preflight.run.complete",
                "Preflight run completed",
                {"path": path, "id": run_result.get("id"), "status": status},
            )
        except (MetadataLoadError, RuntimeError) as exc:
            error_count += 1
            summary.append(
                {
                    "metadataPath": str(path),
                    "status": "error",
                    "error": str(exc),
                }
            )
            emit_progress(
                "batch.preflight.error",
                "Preflight run failed",
                {"path": path, "message": str(exc)},
            )

    overall_status = "attention" if (attention_count or error_count) else "ok"

    result = {
        "action": "batch.preflight",
        "id": "project-catalog",
        "status": overall_status,
        "registryPath": str(registry_path),
        "runs": summary,
        "okCount": ok_count,
        "attentionCount": attention_count,
        "errorCount": error_count,
    }
    emit_progress(
        "batch.preflight.complete",
        "Batch preflight run complete",
        {
            "registryPath": registry_path,
            "status": overall_status,
            "okCount": ok_count,
            "attentionCount": attention_count,
            "errorCount": error_count,
        },
    )
    return result


def parse_link_spec(spec: str) -> Dict[str, str]:
    if not spec:
        return {"type": "doc", "path": ""}
    if ":" in spec:
        link_type, path = spec.split(":", 1)
        return {"type": link_type or "doc", "path": path}
    return {"type": "doc", "path": spec}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Project orchestration driver for n00t.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument(
            "--path",
            type=Path,
            required=True,
            help="Path to the metadata-bearing Markdown document.",
        )
        subparser.add_argument(
            "--registry",
            type=Path,
            default=None,
            help="Optional override for the registry location.",
        )

    add_common(subparsers.add_parser("capture", help="Validate metadata and register it."))
    add_common(
        subparsers.add_parser(
            "sync-github", help="Plan GitHub synchronisation using metadata as the source of truth."
        )
    )
    add_common(
        subparsers.add_parser(
            "sync-erpnext",
            help="Plan ERPNext synchronisation using metadata as the source of truth.",
        )
    )
    add_common(
        subparsers.add_parser(
            "preflight",
            help="Chain capture + sync checks and enforce readiness gates in one run.",
        )
    )
    batch_parser = subparsers.add_parser(
        "batch-preflight",
        help="Run preflight readiness checks across multiple metadata documents.",
    )
    batch_parser.add_argument(
        "--paths",
        type=Path,
        nargs="*",
        default=[],
        help="Explicit metadata documents to include in the batch run.",
    )
    batch_parser.add_argument(
        "--include-registry",
        action="store_true",
        help="Include every registry-sourced document even when --paths are provided.",
    )
    batch_parser.add_argument(
        "--registry",
        type=Path,
        default=None,
        help="Optional registry override when deriving metadata sources.",
    )
    record_parser = subparsers.add_parser(
        "record-idea", help="Create a new idea stub with metadata and register it."
    )
    record_parser.add_argument("--title", required=True, help="Idea title.")
    record_parser.add_argument("--owner", required=True, help="Primary owner for the idea.")
    record_parser.add_argument(
        "--tags", nargs="*", default=[], help="Optional tags aligned with the taxonomy."
    )
    record_parser.add_argument(
        "--sponsors", nargs="*", default=[], help="Sponsor teams or reviewers."
    )
    record_parser.add_argument("--source", default="internal", help="Source descriptor.")
    record_parser.add_argument(
        "--review-days",
        type=int,
        default=30,
        help="Review window in days to set the review_date metadata.",
    )

    record_job_parser = subparsers.add_parser(
        "record-job", help="Create a new job stub with metadata and register it."
    )
    record_job_parser.add_argument("--title", help="Job title.")
    record_job_parser.add_argument("--owner", help="Primary owner for the job.")
    record_job_parser.add_argument(
        "--tags", nargs="*", default=[], help="Optional tags aligned with the taxonomy."
    )
    record_job_parser.add_argument(
        "--sponsors", nargs="*", default=[], help="Sponsor teams or reviewers."
    )
    record_job_parser.add_argument("--source", default="internal", help="Source descriptor.")
    record_job_parser.add_argument(
        "--review-days",
        type=int,
        default=30,
        help="Review window in days to set the review_date metadata.",
    )
    record_job_parser.add_argument(
        "--status",
        default="queued",
        help="Override default job status (queued).",
    )
    record_job_parser.add_argument(
        "--lifecycle",
        default="deliver",
        help="Override lifecycle stage (deliver).",
    )
    record_job_parser.add_argument("--erpnext-project", help="ERPNext project code.")
    record_job_parser.add_argument("--github-project", help="GitHub project URL.")
    record_job_parser.add_argument(
        "--link",
        action="append",
        default=[],
        help="Link spec in the form type:path (e.g. project:n00tropic_HQ/98. Internal-Projects/IP-001).",
    )
    record_job_parser.add_argument(
        "--from",
        dest="from_path",
        type=Path,
        help="Existing brief to clone metadata from (title/owner/tags/links/etc.).",
    )

    ingest_parser = subparsers.add_parser(
        "ingest-markdown",
        help="Attach metadata to an existing markdown document and register it.",
    )
    ingest_parser.add_argument("--path", type=Path, required=True, help="Document path.")
    ingest_parser.add_argument(
        "--kind",
        choices=["idea", "project", "learn", "issue", "job"],
        default="idea",
        help="Classification used to derive metadata defaults.",
    )
    ingest_parser.add_argument("--owner", help="Owner override.")
    ingest_parser.add_argument("--tags", nargs="*", default=[], help="Optional tags list.")
    ingest_parser.add_argument("--status", help="Status override.")
    ingest_parser.add_argument("--lifecycle", help="Lifecycle stage override.")
    ingest_parser.add_argument(
        "--review-days", type=int, default=30, help="Review window used when inserting metadata."
    )
    ingest_parser.add_argument("--id", help="Explicit metadata identifier.")
    ingest_parser.add_argument("--sponsors", nargs="*", default=[], help="Sponsor list.")
    ingest_parser.add_argument("--source", help="Source descriptor.")
    ingest_parser.add_argument("--erpnext-project", help="ERPNext project code.")
    ingest_parser.add_argument("--github-project", help="GitHub project URL.")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _, workspace_root, _ = resolve_roots()
    default_registry = workspace_root / "n00-cortex" / "data" / "catalog" / "projects.json"

    emit_progress(
        "cli.start",
        "Dispatching project orchestration command",
        {"command": args.command},
    )
    try:
        if args.command in {"capture", "sync-github", "sync-erpnext", "preflight"}:
            registry = (
                args.registry if args.registry else default_registry
            )
            path = args.path.resolve()
            if args.command == "capture":
                result = capture(path, registry)
            elif args.command == "sync-github":
                result = sync_github(path, registry)
            elif args.command == "preflight":
                result = preflight(path, registry)
            else:
                result = sync_erpnext(path, registry)
        elif args.command == "batch-preflight":
            registry = args.registry if args.registry else default_registry
            doc_paths: List[Path] = [path.resolve() for path in args.paths]
            if args.include_registry or not doc_paths:
                registry_payload = load_registry(registry)
                doc_paths.extend(registry_source_paths(registry_payload))
            result = batch_preflight(doc_paths, registry)
        elif args.command == "record-idea":
            result = record_idea(
                registry_path=default_registry,
                title=args.title,
                owner=args.owner,
                tags=args.tags,
                sponsors=args.sponsors,
                source=args.source,
                review_days=args.review_days,
            )
        elif args.command == "record-job":
            from_title = None
            from_owner = None
            from_tags: List[str] = []
            from_sponsors: List[str] = []
            from_source = None
            from_review_date = None
            from_erp = None
            from_github = None
            from_links: List[str] = []
            if args.from_path:
                from_doc = extract_metadata(args.from_path.resolve())
                from_payload = from_doc.payload
                from_title = from_payload.get("title")
                from_owner = from_payload.get("owner")
                from_tags = from_payload.get("tags") or []
                from_sponsors = from_payload.get("sponsors") or []
                from_source = from_payload.get("source")
                from_review_date = from_payload.get("review_date")
                from_erp = from_payload.get("erpnext_project")
                from_github = from_payload.get("github_project")
                from_links_raw = from_payload.get("links") or []
                if isinstance(from_links_raw, list):
                    for entry in from_links_raw:
                        if isinstance(entry, dict):
                            link_type = entry.get("type") or "doc"
                            path_val = entry.get("path")
                            if path_val:
                                from_links.append(f"{link_type}:{path_val}")
                # ensure back-link to source
                _, _, org_root = resolve_roots()
                try:
                    rel_path = str(args.from_path.resolve().relative_to(org_root))
                except Exception:  # pragma: no cover - defensive
                    rel_path = str(args.from_path)
                identifier = str(from_payload.get("id") or "")
                link_type = identifier.split("-", 1)[0] if identifier else "doc"
                back_link = f"{link_type}:{rel_path}"
                if back_link not in from_links:
                    from_links.append(back_link)
            title = args.title or from_title
            owner = args.owner or from_owner
            if not title or not owner:
                raise SystemExit("record-job requires --title/--owner or a --from brief providing them.")
            result = record_job(
                registry_path=default_registry,
                title=title,
                owner=owner,
                tags=list(dict.fromkeys((args.tags or []) + (from_tags or []))),
                sponsors=list(dict.fromkeys((args.sponsors or []) + (from_sponsors or []))),
                source=args.source or from_source or "internal",
                review_days=args.review_days,
                review_date_override=str(from_review_date) if from_review_date else None,
                status=args.status,
                lifecycle=args.lifecycle,
                erpnext_project=args.erpnext_project or from_erp,
                github_project=args.github_project or from_github,
                links=list(dict.fromkeys((args.link or []) + from_links)),
            )
        elif args.command == "ingest-markdown":
            result = ingest_markdown(
                registry_path=default_registry,
                path=args.path,
                kind=args.kind,
                owner=args.owner,
                tags=args.tags,
                status=args.status,
                lifecycle=args.lifecycle,
                review_days=args.review_days,
                identifier=args.id,
                sponsors=args.sponsors,
                source=args.source,
                erpnext_project=args.erpnext_project,
                github_project=args.github_project,
            )
        else:
            raise RuntimeError(f"Unsupported command: {args.command}")
    except (MetadataLoadError, RuntimeError) as exc:
        print(f"ERROR: {exc}")
        emit_progress("cli.error", "Command failed", {"command": args.command, "error": str(exc)})
        return 1

    write_artifact(result)
    emit_progress(
        "cli.complete",
        "Command completed successfully",
        {"command": args.command, "status": result.get("status")},
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
