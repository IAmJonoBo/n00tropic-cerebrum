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
from threading import Thread
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[3]
FRONTIERS_ROOT = ROOT / "n00-frontiers"
TOOLCHAIN_MANIFEST = ROOT / "n00-cortex" / "data" / "toolchain-manifest.json"
FRONTIERS_OVERRIDE = (
    ROOT / "n00-cortex" / "data" / "dependency-overrides" / "n00-frontiers.json"
)
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
WATCH_STATUS_TITLE = "Frontiers Evergreen Status"

STATUS_BADGES = {
    "success": "[OK]",
    "failed": "[FAIL]",
    "needs-run": "[RUN]",
    "clean": "[CLEAN]",
    "skipped": "[SKIP]",
}


def _status_badge(status: Optional[str]) -> str:
    label = status or "unknown"
    return f"{STATUS_BADGES.get(label, '[INFO]')} {label}"


def _format_list(values: Optional[List[str]]) -> str:
    if not values:
        return "none"
    cleaned = [str(value) for value in values if value]
    return ", ".join(cleaned) if cleaned else "none"


def _print_status_block(title: str, rows: List[tuple[str, str]]) -> None:
    divider = "-" * 60
    print(f"[evergreen] {divider}")
    print(f"[evergreen] {title}")
    for label, value in rows:
        print(f"[evergreen]   {label:<18}: {value}")
    print(f"[evergreen] {divider}")


def _render_watch_summary(payload: Dict[str, Any], title: str) -> None:
    rows = [
        ("Status", _status_badge(payload.get("status"))),
        ("Changed Targets", _format_list(payload.get("changedTargets"))),
        ("State Path", payload.get("statePath") or "n/a"),
    ]
    _print_status_block(title, rows)


def _render_run_summary(summary: Dict[str, Any]) -> None:
    rows: List[tuple[str, str]] = [
        ("Status", _status_badge(summary.get("status"))),
        ("Exit Code", str(summary.get("exitCode"))),
        ("Duration (s)", str(summary.get("durationSeconds"))),
        ("Changed Targets", _format_list(summary.get("changedTargets"))),
        ("Templates", ", ".join(summary.get("templates", []))),
        ("Command", summary.get("command", "")),
        ("Log", summary.get("logPath", "n/a")),
    ]
    _print_status_block("Frontiers Evergreen Run", rows)


def _render_probe_summary(summary: Dict[str, Any]) -> None:
    rows = [
        ("Status", _status_badge(summary.get("status"))),
        ("Canonical", summary.get("canonical", "n/a")),
        ("Override", summary.get("override", "n/a")),
        ("Allow Lower", str(summary.get("allowLower"))),
        ("Log", summary.get("logPath", "n/a")),
    ]
    _print_status_block("Python Probe", rows)


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


def changed_targets(
    hashes: Dict[str, Optional[str]], state: Dict[str, Any]
) -> List[str]:
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


def _run_with_live_output(
    cmd: List[str], cwd: Path, heartbeat_interval: int = 30
) -> tuple[int, str, str]:
    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    stdout_lines: List[str] = []
    stderr_lines: List[str] = []

    def _consume(pipe: Optional[Any], label: str, collector: List[str]) -> None:
        if pipe is None:
            return
        for line in iter(pipe.readline, ""):
            collector.append(line)
            stripped = line.rstrip()
            if stripped:
                print(f"[evergreen][{label}] {stripped}")
        pipe.close()

    stdout_thread = Thread(
        target=_consume, args=(process.stdout, "stdout", stdout_lines), daemon=True
    )
    stderr_thread = Thread(
        target=_consume, args=(process.stderr, "stderr", stderr_lines), daemon=True
    )
    stdout_thread.start()
    stderr_thread.start()

    start = time.monotonic()
    last_heartbeat = start
    try:
        while process.poll() is None:
            now = time.monotonic()
            if now - last_heartbeat >= heartbeat_interval:
                elapsed = now - start
                print(
                    f"[evergreen] still running ({elapsed:.0f}s elapsed, pid {process.pid})"
                )
                last_heartbeat = now
            time.sleep(1)
    finally:
        process.wait()
        stdout_thread.join()
        stderr_thread.join()

    return process.returncode, "".join(stdout_lines), "".join(stderr_lines)


def _probe_python_requirements(python_version: str) -> Dict[str, Any]:
    log_path = PYTHON_PROBE_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        f"[python-probe] {datetime.now(timezone.utc).isoformat()} Trying Python {python_version}\n",
        encoding="utf-8",
    )

    steps: List[Dict[str, Any]] = []

    def _log_step(
        desc: str, cmd: List[str], result: subprocess.CompletedProcess[Any]
    ) -> None:
        steps.append({"step": desc, "code": result.returncode})
        joined = " ".join(cmd)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n$ {joined}\n")
            if result.stdout:
                handle.write(result.stdout)
            if result.stderr:
                handle.write(result.stderr)

    env = os.environ.copy()
    env.setdefault("UV_PYTHON_DOWNLOADS", "auto")

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

    if not _run(
        "create-venv", ["uv", "venv", "--python", python_version, str(probe_dir)]
    ):
        return {
            "status": "failed",
            "message": "failed to create probe virtualenv",
            "logPath": str(log_path.relative_to(ROOT)),
            "steps": steps,
        }

    python_bin = (
        probe_dir
        / ("Scripts" if sys.platform == "win32" else "bin")
        / ("python.exe" if sys.platform == "win32" else "python")
    )
    requirements = FRONTIERS_ROOT / "requirements.txt"
    if not requirements.exists():
        shutil.rmtree(probe_dir, ignore_errors=True)
        return {
            "status": "skipped",
            "message": f"Missing requirements.txt at {requirements}",
            "logPath": str(log_path.relative_to(ROOT)),
            "steps": steps,
        }

    if not _run("ensurepip", [str(python_bin), "-m", "ensurepip", "--upgrade"]):
        shutil.rmtree(probe_dir, ignore_errors=True)
        return {
            "status": "failed",
            "message": "failed to bootstrap pip via ensurepip",
            "logPath": str(log_path.relative_to(ROOT)),
            "steps": steps,
        }

    if not _run(
        "pip-upgrade", [str(python_bin), "-m", "pip", "install", "--upgrade", "pip"]
    ):
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
        "message": (
            "Installed requirements with canonical python"
            if success
            else "pip install failed"
        ),
        "logPath": str(log_path.relative_to(ROOT)),
        "steps": steps,
    }


def _resolve_python_versions() -> tuple[Optional[str], Optional[str], bool]:
    manifest = _load_json(TOOLCHAIN_MANIFEST)
    toolchains = manifest.get("toolchains", {})
    python_entry = toolchains.get("python", {}) if isinstance(toolchains, dict) else {}
    canonical = python_entry.get("version") if isinstance(python_entry, dict) else None
    override_data = _load_json(FRONTIERS_OVERRIDE)
    overrides = (
        override_data.get("overrides", {}) if isinstance(override_data, dict) else {}
    )
    python_override = overrides.get("python", {}) if isinstance(overrides, dict) else {}
    if not isinstance(python_override, dict):
        return canonical, None, False
    override_value = python_override.get("version")
    override_version = override_value if isinstance(override_value, str) else None
    allow_lower = bool(python_override.get("allow_lower"))
    return canonical, override_version, allow_lower


def _should_probe_python(
    canonical: Optional[str], override_version: Optional[str], allow_lower: bool
) -> bool:
    if not canonical or not override_version or not allow_lower:
        return False
    return _version_tuple(canonical) > _version_tuple(override_version)


def _cached_python_probe(
    state: Dict[str, Any], canonical: str, override_version: str
) -> Optional[Dict[str, Any]]:
    existing = state.get("pythonProbe") if isinstance(state, dict) else None
    if not isinstance(existing, dict):
        return None
    if (
        existing.get("canonical") != canonical
        or existing.get("override") != override_version
    ):
        return None
    timestamp_raw = existing.get("timestamp")
    if not isinstance(timestamp_raw, str):
        return None
    try:
        normalized = timestamp_raw.replace("Z", "+00:00")
        last_run = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if datetime.now(timezone.utc) - last_run < timedelta(
        hours=PYTHON_PROBE_RETENTION_HOURS
    ):
        return existing
    return None


def _execute_python_probe(
    state: Dict[str, Any], canonical: str, override_version: str, allow_lower: bool
) -> Dict[str, Any]:
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
    _render_probe_summary(summary)
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


def maybe_probe_python_alignment(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    canonical, override_version, allow_lower = _resolve_python_versions()
    if not _should_probe_python(canonical, override_version, allow_lower):
        return None
    if canonical is None or override_version is None:
        return None
    cached = _cached_python_probe(state, canonical, override_version)
    if cached:
        return cached
    return _execute_python_probe(state, canonical, override_version, allow_lower)


def run_validation(
    args: argparse.Namespace, hashes: Dict[str, Optional[str]], state: Dict[str, Any]
) -> int:
    cmd = format_command(args)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{DEFAULT_RUN_ID}-{timestamp}"
    log_path = ARTIFACT_DIR / f"{run_id}.log"
    json_path = ARTIFACT_DIR / f"{run_id}.json"

    print(
        f"[evergreen] streaming validator output; full log: {log_path.relative_to(ROOT)}"
    )
    start = time.monotonic()
    return_code, stdout, stderr = _run_with_live_output(cmd, FRONTIERS_ROOT)
    duration = time.monotonic() - start
    write_log(log_path, stdout, stderr)

    summary = {
        "runId": run_id,
        "timestamp": timestamp,
        "command": " ".join(cmd),
        "templates": args.templates or ["*"],
        "forceRebuild": args.force_rebuild,
        "durationSeconds": round(duration, 2),
        "exitCode": return_code,
        "hashes": hashes,
        "changedTargets": changed_targets(hashes, state),
        "logPath": str(log_path.relative_to(ROOT)),
        "artifactPath": str(json_path.relative_to(ROOT)),
    }
    summary["status"] = "success" if return_code == 0 else "failed"
    if state.get("pythonProbe"):
        summary["pythonProbe"] = state["pythonProbe"]

    _render_run_summary(summary)
    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    next_state = dict(state)
    next_state["lastRun"] = summary
    if return_code == 0:
        next_state["hashes"] = hashes
    save_state(next_state)

    print(json.dumps(summary, indent=2))
    return return_code


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
        _render_watch_summary(payload, WATCH_STATUS_TITLE)
        print(json.dumps(payload, indent=2))
        return 0

    if not needs_run and not args.force:
        payload["status"] = "skipped"
        payload["message"] = "No watched changes detected; use --force to run anyway."
        _render_watch_summary(payload, WATCH_STATUS_TITLE)
        print(json.dumps(payload, indent=2))
        return 0

    _render_watch_summary(payload, WATCH_STATUS_TITLE)
    return run_validation(args, hashes, state)


if __name__ == "__main__":
    sys.exit(main())
