#!/usr/bin/env python3
"""Report MCP coverage vs workspace automation scripts to flag new capability candidates."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence, cast

import mcp as mcp_package

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_MCP_PATH = REPO_ROOT / "mcp"
if str(LOCAL_MCP_PATH) not in mcp_package.__path__:
    mcp_package.__path__.append(str(LOCAL_MCP_PATH))

from mcp.capabilities_manifest import (  # type: ignore[import]  # noqa: E402
    CapabilityManifest,
)
from mcp.federation_manifest import (  # type: ignore[import]  # noqa: E402
    FederationManifest,
)

DEFAULT_FEDERATION_PATH = REPO_ROOT / "mcp" / "federation_manifest.json"
CANDIDATE_BASELINE_PATH = REPO_ROOT / "mcp" / "capability_candidates.baseline.json"
CANDIDATE_EXTENSIONS = {".py", ".sh", ".ts", ".js"}
SKIP_FILENAMES = {"__init__.py"}
SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".turbo",
    "dist",
    "build",
    ".mypy_cache",
}
# Explicitly ignore compatibility shims or shared libs that should not become capabilities.
SKIP_PATHS = {
    ".dev/automation/scripts/lib/project_metadata.py",
}


@dataclass
class KnownCapability:
    module: str
    capability_id: str
    entrypoint: Path


@dataclass
class CandidateScript:
    path: Path
    suggested_module: str
    reason: str
    size_bytes: int
    modified_at: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--federation",
        type=Path,
        default=DEFAULT_FEDERATION_PATH,
        help="Path to federation manifest (default: mcp/federation_manifest.json)",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output mode",
    )
    parser.add_argument(
        "--include-root",
        action="append",
        dest="extra_roots",
        help="Additional directories to scan for scripts (relative or absolute)",
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        dest="extensions",
        help="Override candidate file extensions",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        help="Path to candidate baseline (default: mcp/capability_candidates.baseline.json)",
    )
    parser.add_argument(
        "--write-baseline",
        type=Path,
        help="Write the current candidate list to the provided baseline path",
    )
    parser.add_argument(
        "--fail-on-new",
        action="store_true",
        help="Exit 1 if new candidate scripts appear relative to the baseline",
    )
    return parser.parse_args()


def load_known_capabilities(federation_path: Path) -> list[KnownCapability]:
    fed = FederationManifest.load(federation_path, REPO_ROOT)
    known: list[KnownCapability] = []
    for module in fed.modules:
        manifest_path = module.manifest_path(REPO_ROOT)
        repo_root = module.repo_path(REPO_ROOT)
        manifest = CapabilityManifest.load(manifest_path, repo_root)
        for capability in manifest.capabilities:
            entrypoint = capability.resolved_entrypoint(repo_root, manifest_path.parent)
            known.append(
                KnownCapability(
                    module=module.id,
                    capability_id=capability.id,
                    entrypoint=entrypoint,
                )
            )
    return known


def _default_scan_roots() -> list[Path]:
    roots: list[Path] = []
    static_roots = [
        REPO_ROOT / ".dev/automation/scripts",
        REPO_ROOT / "scripts",
    ]
    roots.extend(path.resolve() for path in static_roots if path.exists())
    for module_scripts in REPO_ROOT.glob("*/mcp/scripts"):
        if module_scripts.is_dir():
            roots.append(module_scripts.resolve())
    return roots


def _normalize_extra_roots(extra_roots: Sequence[str] | None) -> list[Path]:
    if not extra_roots:
        return []
    normalized: list[Path] = []
    for root in extra_roots:
        path = Path(root)
        if not path.is_absolute():
            path = (REPO_ROOT / path).resolve()
        if path.is_dir():
            normalized.append(path)
    return normalized


def discover_scan_roots(extra_roots: Sequence[str] | None) -> list[Path]:
    roots = _default_scan_roots() + _normalize_extra_roots(extra_roots)
    deduped: list[Path] = []
    seen = set()
    for root in roots:
        if root in seen:
            continue
        seen.add(root)
        deduped.append(root)
    return deduped


def iter_candidate_files(root: Path, extensions: set[str]) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        # skip hidden files and common build/cache/venv trees
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        rel = path.relative_to(REPO_ROOT)
        if str(rel) in SKIP_PATHS:
            continue
        if path.name.startswith("."):
            continue
        if path.name in SKIP_FILENAMES:
            continue
        if path.suffix.lower() not in extensions:
            continue
        yield path.resolve()


def guess_module(path: Path) -> str:
    parts = path.relative_to(REPO_ROOT).parts
    priorities = [
        "n00-horizons",
        "n00-frontiers",
        "n00-cortex",
        "n00tropic",
        "n00clear-fusion",
        "n00t",
    ]
    for candidate in priorities:
        if candidate in parts:
            return candidate
    if parts and parts[0] == ".dev":
        return "n00t-core"
    return "workspace"


def discover_candidate_scripts(
    known: list[KnownCapability],
    scan_roots: list[Path],
    extensions: set[str],
) -> list[CandidateScript]:
    known_paths = {cap.entrypoint.resolve() for cap in known}
    candidates: list[CandidateScript] = []
    for root in scan_roots:
        for path in iter_candidate_files(root, extensions):
            if path in known_paths:
                continue
            stat = path.stat()
            modified = datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            ).isoformat()
            candidates.append(
                CandidateScript(
                    path=path,
                    suggested_module=guess_module(path),
                    reason="unused-entrypoint",
                    size_bytes=stat.st_size,
                    modified_at=modified,
                )
            )
    candidates.sort(key=lambda item: (item.suggested_module, item.path))
    return candidates


def build_summary(
    known: list[KnownCapability],
    candidates: list[CandidateScript],
    scan_roots: list[Path],
) -> dict[str, object]:
    module_counts = Counter(cap.module for cap in known)
    known_payload = [
        {
            "module": cap.module,
            "id": cap.capability_id,
            "entrypoint": str(cap.entrypoint.relative_to(REPO_ROOT)),
        }
        for cap in known
    ]
    candidate_payload = [
        {
            "path": str(item.path.relative_to(REPO_ROOT)),
            "suggestedModule": item.suggested_module,
            "reason": item.reason,
            "sizeBytes": item.size_bytes,
            "modifiedAt": item.modified_at,
        }
        for item in candidates
    ]
    return {
        "stats": {
            "known": len(known_payload),
            "candidates": len(candidate_payload),
            "modules": module_counts,
            "scanRoots": [str(root.relative_to(REPO_ROOT)) for root in scan_roots],
        },
        "knownCapabilities": known_payload,
        "candidateScripts": candidate_payload,
    }


def render_table(summary: dict[str, object]) -> None:
    stats = cast(dict[str, Any], summary["stats"])
    modules = cast(dict[str, int], stats["modules"])
    module_line = ", ".join(f"{module}:{count}" for module, count in modules.items())
    print(f"Known capabilities: {stats['known']} ({module_line})")
    print(f"Candidate scripts : {stats['candidates']}")
    print("Scan roots:")
    for root in stats["scanRoots"]:
        print(f"  - {root}")
    candidates = cast(list[dict[str, Any]], summary["candidateScripts"])
    if not candidates:
        print("\n✓ No unused scripts detected in the scanned roots.")
        return
    print("\nPotential capability candidates:")
    for item in candidates:
        print(
            f"- {item['path']} -> {item['suggestedModule']}"
            f" ({item['sizeBytes']} bytes, {item['reason']})"
        )


def extract_candidate_paths(summary: dict[str, object]) -> set[str]:
    candidates = cast(list[dict[str, Any]], summary["candidateScripts"])
    return {item["path"] for item in candidates}


def resolve_optional_path(path: Path | None) -> Path | None:
    if path is None:
        return None
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def load_baseline_paths(path: Path) -> set[str]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("candidateScripts", [])
    return {str(item) for item in entries}


def write_baseline(path: Path, candidate_paths: set[str]) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidateScripts": sorted(candidate_paths),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def determine_baseline_path(arg_path: Path | None) -> Path | None:
    resolved = resolve_optional_path(arg_path)
    if resolved:
        return resolved
    if CANDIDATE_BASELINE_PATH.exists():
        return CANDIDATE_BASELINE_PATH
    return None


def apply_baseline_actions(
    summary: dict[str, object],
    baseline_arg: Path | None,
    write_arg: Path | None,
    fail_on_new: bool,
) -> None:
    candidate_paths = extract_candidate_paths(summary)

    write_path = resolve_optional_path(write_arg)
    if write_path:
        write_baseline(write_path, candidate_paths)

    baseline_path = determine_baseline_path(baseline_arg)
    if not baseline_path:
        return

    baseline_paths = load_baseline_paths(baseline_path)
    if not baseline_paths and not baseline_path.exists():
        return

    new_candidates = sorted(candidate_paths - baseline_paths)
    trimmed_baseline = sorted(baseline_paths - candidate_paths)

    if trimmed_baseline:
        print("\nInfo: baseline entries removed (now covered):")
        for path in trimmed_baseline:
            print(f"  - {path}")
    if new_candidates:
        print("\nWarning: new candidate scripts detected:")
        for path in new_candidates:
            print(f"  - {path}")
        if fail_on_new:
            print(
                "\nFailing due to new candidate scripts. Update the baseline or add MCP coverage.",
                file=sys.stderr,
            )
            sys.exit(1)


def main() -> None:
    args = parse_args()
    extensions = (
        {ext.lower() for ext in args.extensions}
        if args.extensions
        else set(CANDIDATE_EXTENSIONS)
    )
    federation_path = args.federation
    if not federation_path.is_absolute():
        federation_path = (REPO_ROOT / federation_path).resolve()
    known = load_known_capabilities(federation_path)
    scan_roots = discover_scan_roots(args.extra_roots)
    candidates = discover_candidate_scripts(known, scan_roots, extensions)
    summary = build_summary(known, candidates, scan_roots)
    if args.format == "json":
        print(json.dumps(summary, indent=2))
    else:
        render_table(summary)
    apply_baseline_actions(
        summary, args.baseline, args.write_baseline, args.fail_on_new
    )


if __name__ == "__main__":
    main()
