#!/usr/bin/env python3
"""Summarise metadata-bearing documents for fast task slicing and handovers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

from lib import project_metadata


def default_documents() -> List[Path]:
    _, workspace_root, org_root = project_metadata.resolve_roots()
    documents: Set[Path] = set()
    documents.update(
        project_metadata.discover_documents(workspace_root / "n00-horizons" / "ideas", ["README.md"])
    )
    documents.update(
        project_metadata.discover_documents(
            workspace_root / "n00-horizons" / "learning-log", ["LL-*.md"], recursive=False
        )
    )
    documents.update(
        project_metadata.discover_documents(org_root / "n00tropic_HQ" / "98. Internal-Projects", ["*.md"])
    )
    return sorted(documents)


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


def summarise(paths: Sequence[Path]) -> List[Dict[str, object]]:
    schema_validator = project_metadata.load_schema(
        project_metadata.resolve_roots()[1] / "n00-cortex" / "schemas" / "project-metadata.schema.json"
    )
    canonical_tags, alias_map = project_metadata.load_tag_taxonomy(
        project_metadata.resolve_roots()[1]
        / "n00-cortex"
        / "data"
        / "catalog"
        / "project-tags.yaml"
    )
    _, _, org_root = project_metadata.resolve_roots()

    summaries: List[Dict[str, object]] = []
    for path in paths:
        try:
            document = project_metadata.extract_metadata(path)
        except project_metadata.MetadataLoadError as exc:
            summaries.append(
                {
                    "id": path.stem,
                    "title": path.name,
                    "path": str(path.relative_to(org_root)),
                    "slice": infer_slice_type(path),
                    "status": "invalid",
                    "errors": [str(exc)],
                    "links": [],
                }
            )
            continue

        errors, warnings, payload = project_metadata.validate_document(
            document, schema_validator, canonical_tags, alias_map
        )
        errors.extend(project_metadata.ensure_paths_exist(document))

        entry: Dict[str, object] = {
            "id": payload.get("id", path.stem),
            "title": payload.get("title", path.stem.replace("-", " ")).strip(),
            "path": str(path.relative_to(org_root)),
            "slice": infer_slice_type(path),
            "lifecycle_stage": payload.get("lifecycle_stage"),
            "status": payload.get("status"),
            "owner": payload.get("owner"),
            "tags": payload.get("tags", []),
            "review_date": payload.get("review_date"),
            "links": payload.get("links", []),
            "warnings": warnings,
            "errors": errors,
        }
        summaries.append(entry)
    return summaries


def print_table(entries: Sequence[Dict[str, object]]) -> None:
    header = f"{'ID':<32} {'Slice':<15} {'Status':<14} {'Lifecycle':<12} Path"
    print(header)
    print("-" * len(header))
    for entry in entries:
        status = entry.get("status") or ""
        lifecycle = entry.get("lifecycle_stage") or ""
        print(
            f"{str(entry.get('id')):<32} {entry.get('slice',''):<15} {status:<14} {lifecycle:<12} {entry.get('path','')}"
        )
        if entry.get("errors"):
            for err in entry["errors"]:
                print(f"    ❌ {err}")
        if entry.get("warnings"):
            for warn in entry["warnings"]:
                print(f"    ⚠️  {warn}")
        links = entry.get("links") or []
        for link in links:
            link_type = link.get("type", "link")
            link_path = link.get("path", "")
            print(f"    ↳ {link_type}: {link_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="Optional explicit documents to summarise.")
    parser.add_argument("--json", type=Path, help="Optional file to write JSON summary to.")
    args = parser.parse_args()

    documents = args.paths if args.paths else default_documents()
    summaries = summarise(documents)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(summaries, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        print_table(summaries)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
