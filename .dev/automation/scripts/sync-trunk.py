#!/usr/bin/env python3
# pylint: disable=missing-function-docstring,line-too-long,invalid-name
"""Synchronise Trunk configuration across the federated workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

ROOT: Path = Path(__file__).resolve().parents[3]
CANONICAL_TRUNK = (
    ROOT / "n00-cortex" / "data" / "trunk" / "base" / ".trunk" / "trunk.yaml"
)


class Mode(Enum):
    CHECK = "check"
    PULL = "pull"
    PUSH = "push"


@dataclass
class RepoTarget:
    name: str
    path: Path
    status: str | None = None
    message: str | None = None


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="Validate downstream copies match canonical (default).",
    )
    mode.add_argument(
        "--pull",
        action="store_true",
        help="Copy canonical config into downstream copies.",
    )
    mode.add_argument("--write", action="store_true", help="Alias for --pull.")
    mode.add_argument(
        "--push",
        action="store_true",
        help="Promote a downstream copy (or explicit source path) to canonical, then fan out.",
    )
    parser.add_argument(
        "--repo",
        action="append",
        dest="repos",
        help="Limit to specific repo(s). Repeat for multiples.",
    )
    parser.add_argument(
        "--json", type=Path, help="Optional path to write a JSON status report."
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Do not fail when a repo lacks a Trunk config.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        help="Explicit trunk.yaml to use as source when pushing. Overrides --push-from.",
    )
    parser.add_argument(
        "--push-from",
        dest="push_from",
        help="Repo name whose trunk.yaml should become canonical during push.",
    )
    parser.add_argument(
        "--canonical",
        type=Path,
        default=CANONICAL_TRUNK,
        help="Override canonical trunk.yaml path (primarily for tests).",
    )
    return parser.parse_args(argv)


def load_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _load_manifest() -> Dict:
    manifest_path = ROOT / "n00-cortex" / "data" / "toolchain-manifest.json"
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"toolchain manifest is invalid JSON: {manifest_path}\n{exc}"
        ) from exc


def discover_repos() -> Dict[str, Path]:
    manifest = _load_manifest()
    repo_defs = manifest.get("repos", {}) if isinstance(manifest, dict) else {}
    candidates: Dict[str, Path] = {}
    for name in repo_defs.keys():
        path = ROOT / name / ".trunk" / "trunk.yaml"
        if path.exists():
            candidates[name] = path

    for trunk_file in ROOT.glob("*/.trunk/trunk.yaml"):
        name = trunk_file.parent.parent.name
        candidates.setdefault(name, trunk_file)

    return dict(sorted(candidates.items()))


def select_targets(
    all_targets: Dict[str, Path], requested: Optional[Iterable[str]]
) -> List[RepoTarget]:
    if not requested:
        return [RepoTarget(name, path) for name, path in all_targets.items()]
    missing: List[str] = []
    selected: List[RepoTarget] = []
    for name in requested:
        if name in all_targets:
            selected.append(RepoTarget(name, all_targets[name]))
        else:
            missing.append(name)
    if missing:
        available = ", ".join(sorted(all_targets))
        raise RuntimeError(
            f"Unknown repo(s) requested: {', '.join(missing)}. Available: {available or '<none>'}."
        )
    return selected


def check_targets(
    reference: str, targets: List[RepoTarget], allow_missing: bool
) -> Tuple[int, List[RepoTarget]]:
    failures = 0
    for target in targets:
        existing = load_text(target.path)
        if existing is None:
            target.status = "missing"
            target.message = "No trunk.yaml present"
            if not allow_missing:
                failures += 1
            print(
                f"[sync-trunk] {target.name}: missing (.trunk/trunk.yaml)",
                file=sys.stderr,
            )
            continue
        if existing == reference:
            target.status = "aligned"
            print(f"[sync-trunk] {target.name}: aligned")
        else:
            target.status = "drift"
            target.message = "Differs from canonical"
            failures += 1
            print(f"[sync-trunk] {target.name}: drift detected", file=sys.stderr)
    return failures, targets


def pull_targets(reference: str, targets: List[RepoTarget]) -> List[RepoTarget]:
    for target in targets:
        write_text(target.path, reference)
        target.status = "updated"
        target.message = "Pulled from canonical"
        print(f"[sync-trunk] {target.name}: updated from canonical")
    return targets


def resolve_push_source(
    args: argparse.Namespace, targets: Dict[str, Path]
) -> Tuple[str, str]:
    if args.source:
        payload = load_text(args.source)
        if payload is None:
            raise RuntimeError(f"Specified source trunk.yaml not found: {args.source}")
        return payload, str(args.source)

    if args.push_from:
        path = targets.get(args.push_from)
        if path is None:
            available = ", ".join(sorted(targets))
            raise RuntimeError(
                f"--push-from '{args.push_from}' not recognised. Available: {available or '<none>'}."
            )
        payload = load_text(path)
        if payload is None:
            raise RuntimeError(
                f"Source repo '{args.push_from}' is missing .trunk/trunk.yaml."
            )
        return payload, str(path)

    requested = args.repos or []
    if len(requested) == 1:
        path = targets.get(requested[0])
        if path is None:
            raise RuntimeError(f"Cannot push; repo '{requested[0]}' not recognised.")
        payload = load_text(path)
        if payload is None:
            raise RuntimeError(
                f"Source repo '{requested[0]}' is missing .trunk/trunk.yaml."
            )
        return payload, str(path)

    raise RuntimeError("Specify --push-from <repo> or --source <path> when pushing.")


def push_targets(
    payload: str, targets: List[RepoTarget], canonical_path: Path
) -> List[RepoTarget]:
    write_text(canonical_path, payload)
    print(f"[sync-trunk] canonical ({canonical_path}): updated from source")
    for target in targets:
        write_text(target.path, payload)
        target.status = "updated"
        target.message = "Promoted from source"
        print(f"[sync-trunk] {target.name}: updated from source")
    return targets


def emit_json(
    report_path: Path,
    mode: Mode,
    canonical_path: Path,
    canonical_hash: Optional[str],
    targets: List[RepoTarget],
    status: str,
) -> None:
    payload = {
        "mode": mode.value,
        "status": status,
        "canonical": str(canonical_path),
        "canonicalHash": canonical_hash,
        "targets": [
            {
                "repo": target.name,
                "path": str(target.path),
                "status": target.status,
                "message": target.message,
            }
            for target in targets
        ],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"[sync-trunk] wrote JSON report → {report_path}")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    mode = Mode.CHECK
    if args.pull or args.write:
        mode = Mode.PULL
    elif args.push:
        mode = Mode.PUSH

    canonical_path = Path(args.canonical)
    canonical_payload = load_text(canonical_path)
    if canonical_payload is None and mode != Mode.PUSH:
        print(
            f"[sync-trunk] canonical trunk.yaml missing at {canonical_path}",
            file=sys.stderr,
        )
        return 2

    all_targets = discover_repos()
    try:
        selected_targets = select_targets(all_targets, args.repos)
    except RuntimeError as exc:
        print(f"[sync-trunk] {exc}", file=sys.stderr)
        return 2

    exit_status = 0
    status_label = "ok"

    if mode == Mode.CHECK:
        failures, results = check_targets(
            canonical_payload or "", selected_targets, args.allow_missing
        )
        exit_status = 0 if failures == 0 else 1
        status_label = "ok" if failures == 0 else "drift"
        targets = results
    elif mode == Mode.PULL:
        if canonical_payload is None:
            print(
                f"[sync-trunk] canonical trunk.yaml missing at {canonical_path}",
                file=sys.stderr,
            )
            return 2
        targets = pull_targets(canonical_payload, selected_targets)
    else:  # push
        try:
            payload, source_path = resolve_push_source(args, all_targets)
        except RuntimeError as exc:
            print(f"[sync-trunk] {exc}", file=sys.stderr)
            return 2
        print(f"[sync-trunk] promoting trunk.yaml from {source_path}")
        targets = push_targets(payload, selected_targets, canonical_path)
        canonical_payload = payload

    if args.json:
        canonical_hash = None
        if canonical_payload is not None:
            canonical_hash = hashlib.sha256(
                canonical_payload.encode("utf-8")
            ).hexdigest()
        try:
            emit_json(
                args.json, mode, canonical_path, canonical_hash, targets, status_label
            )
        except OSError as exc:
            print(f"[sync-trunk] failed to write JSON report: {exc}", file=sys.stderr)
            exit_status = exit_status or 2

    return exit_status


if __name__ == "__main__":
    raise SystemExit(main())
