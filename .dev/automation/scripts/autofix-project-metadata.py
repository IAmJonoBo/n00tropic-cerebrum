#!/usr/bin/env python3
"""Autofix helper for project metadata documents.

Currently normalises tag aliases to their canonical names and can insert missing defaults.
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

from lib.project_metadata import (
    MetadataLoadError,
    discover_documents,
    extract_metadata,
    load_schema,
    load_tag_taxonomy,
    normalise_date_string,
    resolve_roots,
    validate_document,
    write_metadata,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Optional metadata-bearing Markdown documents to fix. When omitted all default locations are scanned.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write updates back to disk. Without this flag the script only reports planned changes.",
    )
    parser.add_argument(
        "--set-default-status",
        action="store_true",
        help="Fill in missing status/lifecycle defaults based on document type (idea/project/learn).",
    )
    parser.add_argument(
        "--review-days",
        type=int,
        default=30,
        help="Default review window (days) when --set-default-status is used and review_date is missing.",
    )
    return parser.parse_args()


DISPLAY_DATE_FMT = "%d-%m-%Y"
DATE_FIELDS = ("review_date", "recorded", "created")


def infer_defaults(
    metadata: Dict[str, object], review_days: int
) -> Tuple[Dict[str, object], List[str]]:
    updates: Dict[str, object] = {}
    notes: List[str] = []
    identifier = str(metadata.get("id", ""))
    today = date.today()
    default_review = (today + timedelta(days=review_days)).strftime(DISPLAY_DATE_FMT)

    if "status" not in metadata or not metadata.get("status"):
        if identifier.startswith("idea-"):
            updates["status"] = "proposed"
        elif identifier.startswith("project-"):
            updates["status"] = "in-definition"
        elif identifier.startswith("learn-"):
            updates["status"] = "recorded"
        else:
            updates["status"] = "draft"
        notes.append(f"set status={updates['status']}")

    if "lifecycle_stage" not in metadata or not metadata.get("lifecycle_stage"):
        if identifier.startswith("idea-"):
            updates["lifecycle_stage"] = "discover"
        elif identifier.startswith("project-"):
            updates["lifecycle_stage"] = "shape"
        elif identifier.startswith("learn-"):
            updates["lifecycle_stage"] = "discover"
        else:
            updates["lifecycle_stage"] = "deliver"
        notes.append(f"set lifecycle_stage={updates['lifecycle_stage']}")

    if not metadata.get("review_date"):
        updates["review_date"] = default_review
        notes.append(f"set review_date={default_review}")

    return updates, notes


def main() -> int:
    args = parse_args()
    _, workspace_root, org_root = resolve_roots()
    schema_path = (
        workspace_root / "n00-cortex" / "schemas" / "project-metadata.schema.json"
    )
    taxonomy_path = (
        workspace_root / "n00-cortex" / "data" / "catalog" / "project-tags.yaml"
    )

    validator = load_schema(schema_path)
    canonical_tags, alias_map = load_tag_taxonomy(taxonomy_path)

    if args.paths:
        documents = sorted({path.resolve() for path in args.paths})
    else:
        documents = sorted(
            set()
            | set(
                discover_documents(
                    workspace_root / "n00-horizons" / "ideas", ["README.md"]
                )
            )
            | set(
                discover_documents(
                    workspace_root / "n00-horizons" / "jobs", ["README.md"]
                )
            )
            | set(
                discover_documents(
                    workspace_root / "n00-horizons" / "learning-log",
                    ["LL-*.md"],
                    recursive=False,
                )
            )
            | set(
                discover_documents(
                    org_root / "n00tropic_HQ" / "98. Internal-Projects", ["*.md"]
                )
            )
        )

    if not documents:
        print("No metadata documents discovered.")
        return 0

    planned_changes = 0
    had_validation_errors = False
    for document_path in documents:
        try:
            document = extract_metadata(document_path)
        except MetadataLoadError as exc:
            print(f"⚠️  Skipping {document_path}: {exc}")
            continue

        errors, warnings, _ = validate_document(
            document, validator, canonical_tags, alias_map
        )
        if errors:
            print(
                f"❌ {document_path}: cannot autofix until validation errors are resolved."
            )
            for error in errors:
                print(f"   • {error}")
            had_validation_errors = True
            continue

        original_tags = document.payload.get("tags", [])
        updated_payload = dict(document.payload)
        change_log: List[str] = []

        if isinstance(original_tags, list):
            canonicalised = []
            for tag in original_tags:
                canonicalised.append(alias_map.get(tag, tag))
                if tag in alias_map:
                    change_log.append(
                        f"canonicalised tag '{tag}' -> '{alias_map[tag]}'"
                    )
            if canonicalised and canonicalised != original_tags:
                updated_payload["tags"] = canonicalised

        if args.set_default_status:
            defaults, notes = infer_defaults(updated_payload, args.review_days)
            if defaults:
                updated_payload.update(defaults)
                change_log.extend(notes)

        for field in DATE_FIELDS:
            value = updated_payload.get(field)
            new_value, note = normalise_date_string(value)
            if note:
                updated_payload[field] = new_value
                change_log.append(f"normalised {field}: {note}")

        if not change_log and not warnings:
            continue

        planned_changes += 1
        print(f"➡️  {document_path}")
        for item in change_log:
            print(f"   • {item}")
        for warning in warnings:
            print(f"   • warning: {warning}")

        if args.apply and change_log:
            document.payload = updated_payload
            write_metadata(document, updated_payload)
            print("   ✅ updated metadata front matter")

    if planned_changes == 0:
        print("No autofix changes required.")
    else:
        print(f"Processed {planned_changes} document(s).")
        if not args.apply:
            print("Run with --apply to persist changes.")

    return 1 if had_validation_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
