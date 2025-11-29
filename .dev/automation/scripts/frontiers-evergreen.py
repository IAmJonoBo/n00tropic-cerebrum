#!/usr/bin/env python3
"""Frontiers evergreen validation orchestrator.

Runs n00-frontiers template validation whenever canonical inputs (toolchain
manifest, catalog) change and records telemetry artifacts for lifecycle radar
and control panel consumers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[3]
FRONTIERS_ROOT = ROOT / "n00-frontiers"
TOOLCHAIN_MANIFEST = ROOT / "n00-cortex" / "data" / "toolchain-manifest.json"
FRONTIERS_OVERRIDE = ROOT / "n00-cortex" / "data" / "dependency-overrides" / "n00-frontiers.json"
CATALOG_JSON = FRONTIERS_ROOT / "catalog.json"
ARTIFACT_DIR = ROOT / ".dev" / "automation" / "artifacts" / "automation"
STATE_PATH = ARTIFACT_DIR / "frontiers-evergreen-state.json"
PYTHON_PROBE_LOG = ARTIFACT_DIR / "frontiers-python-probe.log"
PYTHON_PROBE_RETENTION_HOURS = 24
PYTHON_PROBE_VENV = FRONTIERS_ROOT / ".dev" / ".python-probe-venv"
DEFAULT_RUN_ID = "frontiers-evergreen"

WATCH_TARGETS = {
    "toolchainManifest": TOOLCHAIN_MANIFEST,
    "frontiersCatalog": CATALOG_JSON,
}


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _version_tuple(raw: str) -> tuple[int, ...]:
    parts = []
    for token in raw.split("."):
        if not token:
            continue
        try:
            parts.append(int(token))
        except ValueError:
            break
    return tuple(parts)


def sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_state() -> Dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(payload: Dict[str, object]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def determine_hashes() -> Dict[str, Optional[str]]:
    hashes: Dict[str, Optional[str]] = {}
    for key, target in WATCH_TARGETS.items():
        hashes[key] = sha256(target)
    return hashes


def changed_targets(hashes: Dict[str, Optional[str]], state: Dict[str, Any]) -> List[str]:
    previous = state.get("hashes") or {}
    changed: List[str] = []
    for key, digest in hashes.items():
        if digest != previous.get(key):
            changed.append(key)
    return changed


def format_command(args: argparse.Namespace) -> List[str]:
    cmd = [".dev/validate-templates.sh", "--all"]
    for tmpl in args.templates:
        cmd.extend(["--template", tmpl])
    if args.force_rebuild:
        cmd.append("--force-rebuild")
    return cmd


def write_log(log_path: Path, stdout: str, stderr: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(stdout + "\n--- stderr ---\n" + stderr, encoding="utf-8")


def _probe_python_requirements(python_version: str) -> Dict[str, Any]:
    log_path = PYTHON_PROBE_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        f"[python-probe] {datetime.now(timezone.utc).isoformat()} Trying Python {python_version}\n",
        encoding="utf-8",
    )

    steps: List[Dict[str, Any]] = []

    def _log_step(desc: str, cmd: List[str], result: subprocess.CompletedProcess[Any]) -> None:
        steps.append({"step": desc, "code": result.returncode})
        joined = " ".join(cmd)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n$ {joined}\n")
            if result.stdout:
                handle.write(result.stdout)
            if result.stderr:
                handle.write(result.stderr)

    env = os.environ.copy()
    env.setdefault("UV_PYTHON_DOWNLOADS", "cache")

    def _run(desc: str, cmd: List[str]) -> bool:
        result = subprocess.run(
            cmd,
            cwd=FRONTIERS_ROOT,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        _log_step(desc, cmd, result)
        return result.returncode == 0

    probe_dir = PYTHON_PROBE_VENV
    shutil.rmtree(probe_dir, ignore_errors=True)

    if shutil.which("uv") is None:
        return {
            "status": "skipped",
            "message": "uv executable not found; install uv to enable python probe",
            "logPath": str(log_path.relative_to(ROOT)),
            "steps": steps,
        }

    if not _run("install-interpreter", ["uv", "python", "install", python_version]):
        return {
            "status": "failed",
            "message": "uv could not install requested python",
            "logPath": str(log_path.relative_to(ROOT)),
            "steps": steps,
        }

    if not _run("create-venv", ["uv", "venv", "--python", python_version, str(probe_dir)]):
        return {
            "status": "failed",
            "message": "failed to create probe virtualenv",
            "logPath": str(log_path.relative_to(ROOT)),
            "steps": steps,
        }

    python_bin = probe_dir / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")
    requirements = FRONTIERS_ROOT / "requirements.txt"
    if not requirements.exists():
        shutil.rmtree(probe_dir, ignore_errors=True)
        return {
            "status": "skipped",
            "message": f"Missing requirements.txt at {requirements}",
            "logPath": str(log_path.relative_to(ROOT)),
            "steps": steps,
        }

    if not _run("pip-upgrade", [str(python_bin), "-m", "pip", "install", "--upgrade", "pip"]):
        shutil.rmtree(probe_dir, ignore_errors=True)
        return {
            "status": "failed",
            "message": "pip upgrade failed inside probe venv",
            "logPath": str(log_path.relative_to(ROOT)),
            "steps": steps,
        }

    install_cmd = [str(python_bin), "-m", "pip", "install", "-r", str(requirements)]
    success = _run("pip-install", install_cmd)
    shutil.rmtree(probe_dir, ignore_errors=True)
    return {
        "status": "success" if success else "failed",
        "message": "Installed requirements with canonical python" if success else "pip install failed",
        "logPath": str(log_path.relative_to(ROOT)),
        "steps": steps,
    }


def maybe_probe_python_alignment(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    manifest = _load_json(TOOLCHAIN_MANIFEST)
    canonical = (
        manifest.get("toolchains", {})
        .get("python", {})
        .get("version")
    )
    override_data = _load_json(FRONTIERS_OVERRIDE)
    override_entry = (
        override_data.get("overrides", {})
        .get("python", {})
        if override_data
        else {}
    )
    override_version = override_entry.get("version") if isinstance(override_entry, dict) else None
    allow_lower = bool(override_entry.get("allow_lower")) if isinstance(override_entry, dict) else False

    if not canonical or not override_version:
        return None
    if _version_tuple(canonical) <= _version_tuple(override_version):
        return None
    if not allow_lower:
        return None

    existing = state.get("pythonProbe", {}) if isinstance(state, dict) else {}
    if (
        existing.get("canonical") == canonical
        and existing.get("override") == override_version
    ):
        timestamp_raw = existing.get("timestamp")
        if timestamp_raw:
            try:
                normalized = timestamp_raw.replace("Z", "+00:00")
                last_run = datetime.fromisoformat(normalized)
            except ValueError:
                last_run = None
            if last_run and datetime.now(timezone.utc) - last_run < timedelta(hours=PYTHON_PROBE_RETENTION_HOURS):
                return existing

    probe_result = _probe_python_requirements(canonical)
    summary = {
        **probe_result,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "canonical": canonical,
        "override": override_version,
        "allowLower": allow_lower,
    }
    state["pythonProbe"] = summary
    save_state(state)

    if summary["status"] == "success":
        print(
            json.dumps(
                {
                    "pythonProbe": summary,
                    "message": "Canonical Python succeeded; remove the override to align versions.",
                }
            )
        )
    return summary


def run_validation(args: argparse.Namespace, hashes: Dict[str, Optional[str]], state: Dict[str, Any]) -> int:
    cmd = format_command(args)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{DEFAULT_RUN_ID}-{timestamp}"
    log_path = ARTIFACT_DIR / f"{run_id}.log"
    json_path = ARTIFACT_DIR / f"{run_id}.json"

    start = time.monotonic()
    result = subprocess.run(
        cmd,
        cwd=FRONTIERS_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    duration = time.monotonic() - start
    write_log(log_path, result.stdout, result.stderr)

    summary = {
        "runId": run_id,
        "timestamp": timestamp,
        "command": " ".join(cmd),
        "templates": args.templates or ["*"],
        "forceRebuild": args.force_rebuild,
        "durationSeconds": round(duration, 2),
        "exitCode": result.returncode,
        "hashes": hashes,
        "changedTargets": changed_targets(hashes, state),
        "logPath": str(log_path.relative_to(ROOT)),
        "artifactPath": str(json_path.relative_to(ROOT)),
    }
    summary["status"] = "success" if result.returncode == 0 else "failed"
    if state.get("pythonProbe"):
        summary["pythonProbe"] = state["pythonProbe"]

    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    next_state = dict(state)
    next_state["lastRun"] = summary
    if result.returncode == 0:
        next_state["hashes"] = hashes
    save_state(next_state)

    print(json.dumps(summary, indent=2))
    return result.returncode


def ensure_prereqs() -> None:
    if not FRONTIERS_ROOT.exists():
        raise SystemExit(f"n00-frontiers repo not found at {FRONTIERS_ROOT}")
    for key, target in WATCH_TARGETS.items():
        if not target.exists():
            raise SystemExit(f"Required file for {key} not found: {target}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Frontiers evergreen validator")
    parser.add_argument(
        "--templates",
        action="append",
        default=[],
        help="Limit validation to specific templates (repeatable)",
    )
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force rebuild of template render caches",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force validation even when no watched files changed",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only report whether validation is required",
    )
    return parser.parse_args()


def main() -> int:
    ensure_prereqs()
    args = parse_args()
    state = load_state()
    maybe_probe_python_alignment(state)
    hashes = determine_hashes()
    changed = changed_targets(hashes, state)
    needs_run = bool(changed) or args.force or not state.get("lastRun")

    payload = {
        "needsRun": needs_run,
        "changedTargets": changed,
        "hashes": hashes,
        "statePath": str(STATE_PATH.relative_to(ROOT)) if STATE_PATH.exists() else None,
    }
    payload["status"] = "needs-run" if needs_run else "clean"
    if state.get("pythonProbe"):
        payload["pythonProbe"] = state["pythonProbe"]

    if args.check_only:
        print(json.dumps(payload, indent=2))
        return 0

    if not needs_run and not args.force:
        payload["status"] = "skipped"
        payload["message"] = "No watched changes detected; use --force to run anyway."
        print(json.dumps(payload, indent=2))
        return 0

    return run_validation(args, hashes, state)


if __name__ == "__main__":
    sys.exit(main())
