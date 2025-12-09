#!/usr/bin/env python3
"""Validate capability manifests individually or via the federation manifest."""

from __future__ import annotations

import argparse
import json
import os
import subprocess  # nosec B404 - trusted workspace commands only
import time
from pathlib import Path
from typing import Any, Iterable, List, Optional

import mcp as mcp_package

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_MCP_PATH = REPO_ROOT / "mcp"
if str(LOCAL_MCP_PATH) not in mcp_package.__path__:
    mcp_package.__path__.append(str(LOCAL_MCP_PATH))

from mcp.capabilities_manifest import (  # type: ignore[import] # noqa: E402
    CapabilityManifest,
)
from mcp.federation_manifest import (  # type: ignore[import] # noqa: E402
    FederatedModule,
    FederationManifest,
    HealthCommand,
)

DEFAULT_MANIFEST_PATH = REPO_ROOT / "n00t" / "capabilities" / "manifest.json"
DEFAULT_FEDERATION_PATH = REPO_ROOT / "mcp" / "federation_manifest.json"


def resolve_repo_path(
    path: Optional[Path], default: Path, base: Path = REPO_ROOT
) -> Path:
    target = path or default
    if not target.is_absolute():
        target = (base / target).resolve()
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--manifest",
        type=Path,
        help="Validate a single capability manifest (defaults to n00t manifest)",
    )
    group.add_argument(
        "--federation",
        type=Path,
        help="Validate every module declared in the federation manifest",
    )
    parser.add_argument(
        "--module",
        action="append",
        dest="modules",
        help="Restrict federation validation to specific module IDs",
    )
    parser.add_argument(
        "--run-health",
        action="store_true",
        help="Execute module-level health commands (federation mode only)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON summary",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="Override repo root when resolving entrypoints (manifest mode only)",
    )
    return parser.parse_args()


def _relative_to_repo(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def summarize_manifest(
    manifest_path: Path, repo_root: Path = REPO_ROOT
) -> dict[str, Any]:
    manifest = CapabilityManifest.load(manifest_path, repo_root)
    enabled = [cap.id for cap in manifest.enabled_capabilities()]
    return {
        "manifest": _relative_to_repo(manifest_path),
        "version": manifest.version,
        "enabled": enabled,
        "count": len(enabled),
    }


def run_health_command(command: HealthCommand, cwd: Path) -> dict[str, Any]:
    env = os.environ.copy()
    env.update(command.env)
    start = time.perf_counter()
    try:
        proc = subprocess.run(  # noqa: S603,S607  # nosec B603 - controlled inputs
            command.command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=command.timeoutSeconds,
        )
        status = "ok" if proc.returncode == 0 else "error"
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        code = proc.returncode
    except subprocess.TimeoutExpired as exc:
        status = "timeout"
        stdout = (exc.stdout or "").strip()
        stderr = (exc.stderr or "").strip()
        code = None
    duration = time.perf_counter() - start
    return {
        "label": command.label,
        "command": command.command,
        "status": status,
        "exitCode": code,
        "stdout": stdout[-4000:],
        "stderr": stderr[-4000:],
        "duration": round(duration, 3),
    }


def summarize_module(
    module: FederatedModule,
    manifest_summary: dict[str, Any],
    health_results: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": module.id,
        "summary": module.summary,
        "tags": module.tags,
        "includeInRoot": module.includeInRoot,
        "manifest": manifest_summary,
        "health": list(health_results),
    }


def validate_federation(
    federation_path: Path, modules: List[str] | None, run_health: bool
) -> dict[str, Any]:
    fed = FederationManifest.load(federation_path, REPO_ROOT)
    module_filter = set(modules or [])
    if module_filter:
        missing = module_filter - {m.id for m in fed.modules}
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise SystemExit(f"Unknown module ids: {missing_list}")
    summaries: list[dict[str, Any]] = []
    for module in fed.modules:
        if module_filter and module.id not in module_filter:
            continue
        manifest_summary = summarize_manifest(
            module.manifest_path(REPO_ROOT), module.repo_path(REPO_ROOT)
        )
        health_results: list[dict[str, Any]] = []
        if run_health and module.health.commands:
            for command in module.health.commands:
                health_results.append(
                    run_health_command(command, module.repo_path(REPO_ROOT))
                )
        summaries.append(summarize_module(module, manifest_summary, health_results))
    return {
        "federation": str(federation_path.relative_to(REPO_ROOT)),
        "modules": summaries,
        "count": len(summaries),
    }


def print_manifest(summary: dict[str, Any]) -> None:
    enabled = ", ".join(summary["enabled"])
    print(f"Manifest: {summary['manifest']}")
    print(f"Version : {summary['version']}")
    print(f"Enabled : {summary['count']} -> {enabled}")


def print_federation(summary: dict[str, Any]) -> None:
    print(
        f"Federation: {summary['federation']} (modules validated: {summary['count']})"
    )
    for module in summary["modules"]:
        manifest = module["manifest"]
        line = f"- {module['id']}: {manifest['count']} enabled / {manifest['manifest']}"
        print(line)
        if module["health"]:
            for health in module["health"]:
                print(
                    f"    · {health['label']}: {health['status']}"
                    f" ({health['duration']}s)"
                )


def main() -> None:
    args = parse_args()
    repo_root_override: Path | None = None
    if args.repo_root:
        override = args.repo_root
        if not override.is_absolute():
            override = (Path.cwd() / override).resolve()
        else:
            override = override.resolve()
        repo_root_override = override
    if args.federation:
        federation_path = resolve_repo_path(args.federation, DEFAULT_FEDERATION_PATH)
        modules = args.modules or []
        summary = validate_federation(federation_path, modules, args.run_health)
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print_federation(summary)
        return

    base_root = repo_root_override or REPO_ROOT
    manifest_path = resolve_repo_path(
        args.manifest, DEFAULT_MANIFEST_PATH, base=base_root
    )
    summary = summarize_manifest(manifest_path, base_root)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print_manifest(summary)


if __name__ == "__main__":
    main()
