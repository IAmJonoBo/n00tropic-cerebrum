#!/usr/bin/env python3
"""Automatically repair metadata links (paths and reciprocity)."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from lib import project_metadata


@dataclass
class LinkReference:
    source_id: str
    source_path: str
    link_type: str


def relative_to_org(path: Path, org_root: Path) -> str:
    path_obj = Path(path)
    try:
        return str(path_obj.resolve().relative_to(org_root))
    except ValueError:
        return str(path_obj.resolve())


def infer_link_type(identifier: Optional[str]) -> str:
    if not identifier:
        return "doc"
    prefix = identifier.split("-", 1)[0]
    mapping = {
        "idea": "idea",
        "project": "project",
        "learn": "learning-log",
        "job": "job",
        "adr": "adr",
    }
    return mapping.get(prefix, "doc")


def discover_metadata_paths() -> List[Path]:
    _, workspace_root, org_root = project_metadata.resolve_roots()
    paths: List[Path] = []
    paths.extend(
        project_metadata.discover_documents(
            workspace_root / "n00-horizons" / "ideas", ["README.md"]
        )
    )
    paths.extend(
        project_metadata.discover_documents(
            workspace_root / "n00-horizons" / "learning-log",
            ["LL-*.md"],
            recursive=False,
        )
    )
    paths.extend(
        project_metadata.discover_documents(
            workspace_root / "n00-horizons" / "jobs", ["README.md"]
        )
    )
    paths.extend(
        project_metadata.discover_documents(
            org_root / "n00tropic_HQ" / "98. Internal-Projects", ["*.md"]
        )
    )
    return sorted(set(path.resolve() for path in paths))


def canonicalize_link_path(
    document_path: Path,
    raw_path: str,
    org_root: Path,
    stem_index: Dict[str, List[Path]],
) -> Tuple[Optional[str], Optional[str]]:
    if not raw_path:
        return None, "missing path"
    if raw_path.startswith(("http://", "https://", "mailto:")):
        return raw_path, "external"

    candidates: List[Path] = []
    raw = Path(raw_path)
    if raw.is_absolute():
        candidates.append(raw)
    if raw_path.startswith("n00"):
        candidates.append((org_root / raw_path).resolve())
    if raw_path.startswith(".dev"):
        candidates.append((org_root / raw_path).resolve())
    candidates.append((document_path.parent / raw_path).resolve())
    for candidate in candidates:
        if candidate.exists():
            try:
                candidate.relative_to(org_root)
            except ValueError:
                continue
            return str(candidate.relative_to(org_root)), None
    stem = raw.stem
    if stem and stem in stem_index:
        matches = stem_index[stem]
        if len(matches) == 1:
            target = matches[0].resolve()
            return str(target.relative_to(org_root)), "resolved by stem"
        return None, "ambiguous stem"
    return None, "target not found"


def normalise_links(
    document_path: Path,
    links: Iterable[Dict[str, object]],
    org_root: Path,
    stem_index: Dict[str, List[Path]],
) -> Tuple[List[Dict[str, str]], List[Dict[str, object]]]:
    new_links: List[Dict[str, str]] = []
    issues: List[Dict[str, object]] = []
    seen = set()
    for entry in links:
        if not isinstance(entry, dict):
            issues.append({"type": "warning", "message": "dropped non-dict link entry"})
            continue
        link_type = str(entry.get("type") or "doc")
        raw_path = str(entry.get("path") or "")
        target, reason = canonicalize_link_path(
            document_path, raw_path, org_root, stem_index
        )
        if not target:
            issues.append(
                {
                    "type": "warning",
                    "message": f"unresolved path '{raw_path}' ({reason})",
                }
            )
            # retain original link so intent is preserved
            target = raw_path
        canonical = target
        key = (link_type, canonical)
        if key in seen:
            continue
        seen.add(key)
        if reason and reason != "external":
            issues.append(
                {
                    "type": "info",
                    "message": f"resolved {raw_path} -> {canonical} ({reason})",
                }
            )
        new_links.append({"type": link_type, "path": canonical})
    return sorted(new_links, key=lambda item: (item["type"], item["path"])), issues


def build_reverse_link_index(
    documents: Dict[Path, project_metadata.MetadataDocument],
    org_root: Path,
    stem_index: Dict[str, List[Path]],
) -> Dict[str, List[LinkReference]]:
    reverse_map: Dict[str, List[LinkReference]] = defaultdict(list)
    for path, document in documents.items():
        payload = document.payload
        doc_id = str(payload.get("id") or path.stem)
        links = payload.get("links") or []
        if not isinstance(links, list):
            continue
        for entry in links:
            if not isinstance(entry, dict):
                continue
            raw_path = str(entry.get("path") or "")
            target, reason = canonicalize_link_path(
                path, raw_path, org_root, stem_index
            )
            if not target or reason == "external":
                continue
            canonical = relative_to_org(target, org_root)
            reverse_map[canonical].append(
                LinkReference(
                    source_id=doc_id,
                    source_path=relative_to_org(path, org_root),
                    link_type=entry.get("type") or infer_link_type(doc_id),
                )
            )
    return reverse_map


def autofix_document(
    document_path: Path,
    document: project_metadata.MetadataDocument,
    org_root: Path,
    stem_index: Dict[str, List[Path]],
    reverse_map: Dict[str, List[LinkReference]],
    apply_changes: bool,
) -> Dict[str, object]:
    payload = dict(document.payload)
    existing_links = payload.get("links")
    if not isinstance(existing_links, list):
        existing_links = []
    canonical_links, issues = normalise_links(
        document.path, existing_links, org_root, stem_index
    )

    referrers = reverse_map.get(relative_to_org(document.path, org_root), [])
    for ref in referrers:
        entry = {"type": infer_link_type(ref.source_id), "path": ref.source_path}
        if entry not in canonical_links:
            canonical_links.append(entry)
            issues.append(
                {
                    "type": "info",
                    "message": f"added reciprocal link to {ref.source_id}",
                }
            )
    canonical_links = sorted(
        canonical_links, key=lambda item: (item["type"], item["path"])
    )

    changed = canonical_links != existing_links
    if apply_changes and changed:
        payload["links"] = canonical_links
        project_metadata.write_metadata(document, payload)

    return {
        "action": "autofix.links",
        "id": payload.get("id", document.path.stem),
        "metadataPath": relative_to_org(document.path, org_root),
        "status": "changed" if changed else "skipped",
        "before": existing_links or [],
        "after": canonical_links,
        "changes": issues,
        "links": canonical_links,
    }


def write_artifact(result: Dict[str, object], org_root: Path) -> Path:
    artifact_dir = (
        org_root / ".dev" / "automation" / "artifacts" / "project-autofix-links"
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / f"{result.get('id', 'unknown')}-autofix_links.json"
    artifact_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return artifact_path


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Autofix metadata link entries.")
    parser.add_argument(
        "--path",
        type=Path,
        action="append",
        help="Specific metadata documents to process (repeatable).",
    )
    parser.add_argument(
        "--all", action="store_true", help="Process every known metadata document."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist fixes to disk (default is dry-run).",
    )
    args = parser.parse_args(argv)

    targets: List[Path] = []
    if args.path:
        targets.extend(path.resolve() for path in args.path)
    if args.all or not targets:
        targets.extend(discover_metadata_paths())
    targets = sorted(set(targets))
    if not targets:
        raise SystemExit("No metadata documents supplied.")

    _, _, org_root = project_metadata.resolve_roots()
    documents: Dict[Path, project_metadata.MetadataDocument] = {}
    stem_index: Dict[str, List[Path]] = defaultdict(list)
    for path in targets + discover_metadata_paths():
        resolved = path.resolve()
        if resolved in documents:
            continue
        try:
            doc = project_metadata.extract_metadata(resolved)
        except project_metadata.MetadataLoadError:
            continue
        documents[resolved] = doc
        stem_index[resolved.stem].append(resolved)

    reverse_map = build_reverse_link_index(documents, org_root, stem_index)

    status_counts = {"changed": 0, "skipped": 0, "error": 0}
    for target in targets:
        resolved = target.resolve()
        try:
            document = documents.get(resolved) or project_metadata.extract_metadata(
                resolved
            )
        except project_metadata.MetadataLoadError as exc:
            result = {
                "action": "autofix.links",
                "id": resolved.stem,
                "metadataPath": relative_to_org(resolved, org_root),
                "status": "error",
                "error": str(exc),
            }
            write_artifact(result, org_root)
            print(json.dumps(result))
            status_counts["error"] += 1
            continue
        result = autofix_document(
            resolved, document, org_root, stem_index, reverse_map, args.apply
        )
        artifact_path = write_artifact(result, org_root)
        result["artifactPath"] = str(artifact_path)
        print(json.dumps(result))
        status_counts[result["status"]] += 1

    summary = {
        "action": "autofix.links.summary",
        "status": "ok" if not status_counts["error"] else "attention",
        "changed": status_counts["changed"],
        "skipped": status_counts["skipped"],
        "errors": status_counts["error"],
    }
    print(json.dumps(summary))
    return 0 if not status_counts["error"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
