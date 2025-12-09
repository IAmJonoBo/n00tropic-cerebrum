#!/usr/bin/env python3
"""Shared helpers for n00tropic project metadata validation and orchestration."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import yaml  # type: ignore[import-not-found]
from jsonschema import Draft202012Validator  # type: ignore[import-not-found]
from jsonschema.exceptions import ValidationError  # type: ignore[import-not-found]

FRONT_MATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*", re.DOTALL)
DISPLAY_DATE_FMT = "%d-%m-%Y"
ISO_DATE_FMT = "%Y-%m-%d"
DATE_FORMATS = (DISPLAY_DATE_FMT, ISO_DATE_FMT)


@dataclass
class MetadataDocument:
    """Represents a metadata-bearing Markdown document."""

    path: Path
    payload: Dict[str, object]
    raw_front_matter: str
    match_span: Tuple[int, int]


class MetadataLoadError(RuntimeError):
    """Raised when metadata cannot be parsed from a document."""


def resolve_roots() -> Tuple[Path, Path, Path]:
    """
    Returns (frontiers_root, workspace_root, org_root).

    frontiers_root – the n00-frontiers repository root
    workspace_root – the n00tropic-cerebrum workspace root
    org_root – the organisational root containing repositories and HQ docs
    """
    env_override = os.environ.get("N00_ORG_ROOT")
    candidate = (
        Path(env_override).expanduser().resolve()
        if env_override
        else Path(__file__).resolve().parents[4]
    )

    # If the candidate already points at the workspace root, lift org_root one level up.
    if candidate.name == "n00tropic-cerebrum":
        org_root = candidate.parent
        workspace_root = candidate
    else:
        org_root = candidate
        workspace_root = candidate / "n00tropic-cerebrum"

    frontiers_root = workspace_root / "n00-frontiers"
    return frontiers_root, workspace_root, org_root


def extract_metadata(document: Path) -> MetadataDocument:
    """Extracts YAML front matter from a Markdown document."""
    text = document.read_text(encoding="utf-8")
    match = FRONT_MATTER_PATTERN.match(text)
    if not match:
        raise MetadataLoadError(f"{document} missing YAML front matter block")
    raw_front_matter = match.group(1)
    data = yaml.safe_load(raw_front_matter) or {}
    if not isinstance(data, dict):
        raise MetadataLoadError(f"{document} metadata must be a mapping object")
    return MetadataDocument(
        path=document,
        payload=data,
        raw_front_matter=raw_front_matter,
        match_span=match.span(),
    )


def load_schema(schema_path: Path) -> Draft202012Validator:
    """Creates a JSON Schema validator from the supplied schema path."""
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def load_tag_taxonomy(taxonomy_path: Path) -> Tuple[Set[str], Dict[str, str]]:
    """
    Returns (canonical_tags, alias_map) from the taxonomy file.

    canonical_tags – set of allowed tag slugs (e.g. governance/project-management)
    alias_map – mapping of alias -> canonical tag
    """
    data = yaml.safe_load(taxonomy_path.read_text(encoding="utf-8")) or {}
    hierarchy = data.get("hierarchy", {})
    canonical_tags: Set[str] = set()
    alias_map: Dict[str, str] = {}

    def _walk(node: dict, trail: List[str]) -> None:
        canonical = "/".join(trail)
        if canonical:
            canonical_tags.add(canonical)
        aliases = node.get("aliases", [])
        for alias in aliases or []:
            alias_map[str(alias)] = canonical

        for key, value in node.items():
            if key in {"description", "aliases"}:
                continue
            if isinstance(value, dict):
                _walk(value, trail + [key])

    for key, value in hierarchy.items():
        if isinstance(value, dict):
            _walk(value, [key])
        else:
            canonical_tags.add(str(key))

    return canonical_tags, alias_map


def discover_documents(
    base: Path, patterns: Sequence[str], recursive: bool = True
) -> List[Path]:
    """Return all Markdown files matching the provided glob patterns under the base."""
    matches: Set[Path] = set()
    if not base.exists():
        return []
    for pattern in patterns:
        if recursive:
            matches.update(base.glob(f"**/{pattern}"))
        else:
            matches.update(base.glob(pattern))
    return sorted(matches)


def validate_document(
    document: MetadataDocument,
    validator: Draft202012Validator,
    canonical_tags: Set[str],
    alias_map: Dict[str, str],
) -> Tuple[List[str], List[str], Dict[str, object]]:
    """
    Validate a MetadataDocument and return (errors, warnings, normalised_payload).

    normalised_payload extends the original payload with derived fields.
    """
    errors: List[str] = []
    warnings: List[str] = []

    try:
        validator.validate(document.payload)
    except ValidationError as exc:
        errors.append(f"{document.path}: {exc.message}")

    tags = document.payload.get("tags", [])
    normalised_tags: List[str] = []
    if isinstance(tags, list):
        for tag in tags:
            if not isinstance(tag, str):
                errors.append(
                    f"{document.path}: tag values must be strings (found {tag!r})"
                )
                continue
            if tag in canonical_tags:
                normalised_tags.append(tag)
                continue
            if tag in alias_map:
                canonical = alias_map[tag]
                normalised_tags.append(canonical)
                warnings.append(
                    f"{document.path}: tag '{tag}' is an alias for canonical '{canonical}'"
                )
            else:
                errors.append(
                    f"{document.path}: tag '{tag}' not present in taxonomy (project-tags.yaml)"
                )
    else:
        errors.append(f"{document.path}: tags must be an array of strings")

    normalised_payload = dict(document.payload)
    if normalised_tags:
        normalised_payload["tags"] = normalised_tags

    return errors, warnings, normalised_payload


def ensure_paths_exist(document: MetadataDocument) -> List[str]:
    """Ensure paths referenced in the document's `links` field exist (local paths only)."""
    errors: List[str] = []
    links = document.payload.get("links", [])
    if not links:
        return errors
    if not isinstance(links, list):
        return [f"{document.path}: links must be a list of objects"]
    _, workspace_root, org_root = resolve_roots()
    for entry in links:
        if not isinstance(entry, dict):
            errors.append(f"{document.path}: link entries must be mappings")
            continue
        target = entry.get("path")
        if not target:
            errors.append(f"{document.path}: link entry missing 'path'")
            continue
        # allow external references
        target_str = str(target)
        if target_str.startswith(("http://", "https://", "mailto:")):
            continue
        path_obj = Path(str(target))
        candidates = [(document.path.parent / path_obj).resolve()]
        if not path_obj.is_absolute():
            candidates.append((org_root / path_obj).resolve())
            candidates.append((workspace_root / path_obj).resolve())
        else:
            candidates.append(path_obj)
        if not any(candidate.exists() for candidate in candidates):
            errors.append(f"{document.path}: linked path does not exist -> {target}")
    return errors


def write_metadata(document: MetadataDocument, payload: Dict[str, object]) -> None:
    """Rewrite the YAML front matter of a document with the provided payload."""
    text = document.path.read_text(encoding="utf-8")
    _, end = document.match_span
    front_matter = yaml.safe_dump(payload, sort_keys=False).strip()
    new_header = f"---\n{front_matter}\n---\n"
    remainder = text[end:]
    tmp_path = document.path.with_suffix(document.path.suffix + ".tmp")
    tmp_path.write_text(new_header + remainder, encoding="utf-8")
    tmp_path.replace(document.path)


def parse_date(value: Optional[str]) -> Optional[datetime]:
    """Parse a date string in known formats; returns None if parsing fails."""
    if not value or not isinstance(value, str):
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def format_display_date(value: datetime) -> str:
    """Format a datetime as DD-MM-YYYY."""
    return value.strftime(DISPLAY_DATE_FMT)


def normalise_date_string(raw: object) -> Tuple[object, Optional[str]]:
    """Coerce date strings into display format, returning (new_value, note)."""
    if not raw or not isinstance(raw, str):
        return raw, None
    parsed = parse_date(raw)
    if not parsed:
        return raw, None
    formatted = format_display_date(parsed)
    if formatted != raw:
        return formatted, f"{raw} -> {formatted}"
    return raw, None


def find_duplicate_ids(documents: Iterable[MetadataDocument]) -> List[str]:
    """Return a list of duplicate metadata IDs."""
    seen: Dict[str, Path] = {}
    duplicates: List[str] = []
    for doc in documents:
        identifier = str(doc.payload.get("id") or doc.path.stem)
        if identifier in seen and identifier not in duplicates:
            duplicates.append(identifier)
        else:
            seen[identifier] = doc.path
    return duplicates
