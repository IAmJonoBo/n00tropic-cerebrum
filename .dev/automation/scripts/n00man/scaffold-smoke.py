#!/usr/bin/env python3
"""Run n00man-scaffold inside a sandbox to verify docs/registry overrides."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[4]
N00MAN_ROOT = ROOT / "n00man"
DOCS_ROOT = N00MAN_ROOT / "docs"
SCAFFOLD_SCRIPT = Path(__file__).with_name("n00man-scaffold.py")
DEFAULT_DESCRIPTION = "Smoke-test agent generated via scaffold-smoke harness"
ARTIFACT_ROOT = ROOT / ".dev/automation/artifacts/n00man"


def _copy_docs_tree(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(DOCS_ROOT, destination, dirs_exist_ok=True)


def _prepare_sandbox(path_override: str | None, keep: bool) -> tuple[Path, Path | None]:
    if path_override:
        docs_root = Path(path_override).expanduser().resolve()
        _copy_docs_tree(docs_root)
        return docs_root, None
    temp_root = Path(tempfile.mkdtemp(prefix="n00man-scaffold-")).resolve()
    docs_root = temp_root / "docs"
    _copy_docs_tree(docs_root)
    cleanup_root: Path | None = None if keep else temp_root
    return docs_root, cleanup_root


def _run_scaffold(command: List[str]) -> dict[str, object]:
    proc = subprocess.run(command, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        raise SystemExit(proc.returncode)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        sys.stderr.write(proc.stdout)
        raise SystemExit(f"Failed to parse scaffold output: {exc}") from exc
    return payload


def _write_artifact(payload: dict[str, object]) -> Path:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_path = ARTIFACT_ROOT / f"scaffold-smoke-{timestamp}.json"
    artifact_payload = dict(payload)
    artifact_payload.setdefault("timestamp", timestamp)
    artifact_path.write_text(json.dumps(artifact_payload, indent=2), encoding="utf-8")
    return artifact_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-id", default="smoke-analyst")
    parser.add_argument("--name")
    parser.add_argument("--role", default="analyst")
    parser.add_argument("--description", default=DEFAULT_DESCRIPTION)
    parser.add_argument("--owner")
    parser.add_argument("--status")
    parser.add_argument(
        "--sandbox-root", help="Optional docs root to reuse for sandboxing"
    )
    parser.add_argument(
        "--keep-sandbox",
        action="store_true",
        help="Preserve the temporary sandbox directory for inspection",
    )
    parser.add_argument(
        "scaffold_args",
        nargs=argparse.REMAINDER,
        help=textwrap.dedent(
            """Additional arguments passed to n00man-scaffold. Use '--' before the first argument"""
        ),
    )
    args = parser.parse_args()

    docs_root, cleanup_root = _prepare_sandbox(args.sandbox_root, args.keep_sandbox)
    registry_path = docs_root / "agent-registry.json"
    if not registry_path.exists():
        registry_path.write_text(
            json.dumps({"schema_version": "1.0", "agents": []}, indent=2),
            encoding="utf-8",
        )

    command: list[str] = [
        sys.executable,
        str(SCAFFOLD_SCRIPT),
        "--agent-id",
        args.agent_id,
        "--role",
        args.role,
        "--description",
        args.description,
        "--docs-root",
        str(docs_root),
        "--registry-path",
        str(registry_path),
    ]
    if args.name:
        command.extend(["--name", args.name])
    if args.owner:
        command.extend(["--owner", args.owner])
    if args.status:
        command.extend(["--status", args.status])
    if args.scaffold_args:
        extras = args.scaffold_args
        if extras and extras[0] == "--":
            extras = extras[1:]
        command.extend(extras)

    payload = _run_scaffold(command)
    if payload.get("status") != "success":
        print(json.dumps(payload, indent=2))
        return 2

    generated = [Path(path) for path in payload.get("generated_files", [])]
    outside_docs = [path for path in generated if docs_root not in path.parents]
    summary = {
        "status": "success",
        "docs_root": str(docs_root),
        "registry_path": str(registry_path),
        "generated_files": [str(path) for path in generated],
        "sandbox_kept": args.keep_sandbox or args.sandbox_root is not None,
    }
    if outside_docs:
        summary["warning"] = "Some generated files fell outside the sandbox"

    artifact_path = _write_artifact(summary)
    summary["artifact_path"] = str(artifact_path)
    print(json.dumps(summary, indent=2))

    if cleanup_root and cleanup_root.exists():
        shutil.rmtree(cleanup_root, ignore_errors=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
