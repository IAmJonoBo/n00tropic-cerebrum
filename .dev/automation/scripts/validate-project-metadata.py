#!/usr/bin/env python3
"""Validate metadata-bearing documents against the project schema and taxonomy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Set

from lib.project_metadata import (
    MetadataLoadError,
    discover_documents,
    ensure_paths_exist,
    extract_metadata,
    load_schema,
    load_tag_taxonomy,
    resolve_roots,
    validate_document,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Optional explicit metadata documents to validate. When omitted, the standard "
        "workspace directories are scanned automatically.",
    )
    parser.add_argument(
        "--json",
        type=Path,
        help="Optional path to write a machine-readable validation summary.",
    )
    return parser.parse_args()


def discover_default_documents() -> Set[Path]:
    _, workspace_root, org_root = resolve_roots()
    documents: Set[Path] = set()
    documents.update(
        discover_documents(workspace_root / "n00-horizons" / "ideas", ["README.md"])
    )
    documents.update(
        discover_documents(workspace_root / "n00-horizons" / "jobs", ["README.md"])
    )
    documents.update(
        discover_documents(
            workspace_root / "n00-horizons" / "learning-log",
            ["LL-*.md"],
            recursive=False,
        )
    )
    documents.update(
        discover_documents(
            org_root / "n00tropic_HQ" / "98. Internal-Projects", ["*.md"]
        )
    )
    return documents


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

    documents = (
        {path.resolve() for path in args.paths}
        if args.paths
        else discover_default_documents()
    )

    errors: List[str] = []
    warnings: List[str] = []
    validated: List[Dict[str, object]] = []

    for path in sorted(documents):
        try:
            document = extract_metadata(path)
        except MetadataLoadError as exc:
            errors.append(str(exc))
            continue

        doc_errors, doc_warnings, normalised_payload = validate_document(
            document, validator, canonical_tags, alias_map
        )
        errors.extend(doc_errors)
        warnings.extend(doc_warnings)
        errors.extend(ensure_paths_exist(document))

        normalised_payload.update(
            {
                "_path": str(path),
                "_workspace_relative": str(path.relative_to(org_root)),
            }
        )
        validated.append(normalised_payload)

    ids_to_paths: Dict[str, Path] = {}
    for payload in validated:
        metadata_id = payload.get("id")
        if not isinstance(metadata_id, str):
            continue
        existing = ids_to_paths.get(metadata_id)
        if existing and existing != Path(payload["_path"]):
            errors.append(
                f"Duplicate metadata id '{metadata_id}' found in {existing} and {payload['_path']}"
            )
        else:
            ids_to_paths[metadata_id] = Path(payload["_path"])

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                {
                    "validated": validated,
                    "errors": errors,
                    "warnings": warnings,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        if warnings:
            print("Warnings encountered:")
            for warning in sorted(set(warnings)):
                print(f"  - {warning}")
        return 1

    print(f"Validated {len(validated)} metadata documents successfully.")
    if warnings:
        print("Warnings encountered:")
        for warning in sorted(set(warnings)):
            print(f"  - {warning}")
        print(
            "➡️  Run `.dev/automation/scripts/autofix-project-metadata.py --apply` to normalise tags."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
