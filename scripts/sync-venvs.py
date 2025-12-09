#!/usr/bin/env python3
"""
Sync per-repo Python virtual environments using workspace manifest.

Defaults:
  - Reads automation/workspace.manifest.json
  - Creates venv at manifest["venv"] (fallback: <repo>/.venv-<name> or .venv)
  - Installs requirements in priority order:
      requirements.txt, requirements-dev.txt, requirements-doctr.txt (if present)
  - Uses uv; installs uv if missing.
  - Mode `auto` (default) prefers pinned sync if lockfiles exist, else resolves.
  - Mode `install` resolves transitive deps (`uv pip install -r ...`).
    Mode `sync` expects fully pinned requirement files (`uv pip sync ...`).

Examples:
  python3 scripts/sync-venvs.py --all --check
  python3 scripts/sync-venvs.py --repo n00t --full --check
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess  # trunk-ignore(bandit/B404): CLI orchestration requires subprocess usage.
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "automation" / "workspace.manifest.json"
UV_INSTALL_URL = "https://astral.sh/uv/install.sh"


def _run_command(cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a subprocess with strict defaults."""
    return subprocess.run(cmd, check=True, **kwargs)  # trunk-ignore(bandit/B603)


def _run_uv_installer() -> None:
    """Download the official uv installer script and execute it securely."""
    if shutil.which("curl"):
        fetch_cmd = ["curl", "-LsSf", UV_INSTALL_URL]
    elif shutil.which("wget"):
        fetch_cmd = ["wget", "-qO-", UV_INSTALL_URL]
    else:
        raise SystemExit(
            "[sync-venvs] uv missing and neither curl nor wget is available to download the installer."
        )
    result = _run_command(fetch_cmd, stdout=subprocess.PIPE)
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(result.stdout)
        script_path = Path(handle.name)
    script_path.chmod(0o755)
    shell_path = shutil.which("sh")
    if not shell_path:
        raise SystemExit(
            "[sync-venvs] Unable to locate POSIX shell for uv installation."
        )
    try:
        _run_command([shell_path, str(script_path)])
    finally:
        script_path.unlink(missing_ok=True)


def ensure_uv() -> Path:
    uv = shutil.which("uv")
    if uv:
        return Path(uv)
    print("[sync-venvs] uv not found; installing via Astral script…", file=sys.stderr)
    _run_uv_installer()
    uv = shutil.which("uv")
    if not uv:
        raise SystemExit("[sync-venvs] uv installation failed; aborting.")
    return Path(uv)


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        raise SystemExit(f"[sync-venvs] manifest missing: {MANIFEST_PATH}")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def requirement_files(repo_root: Path, include_full: bool) -> List[Path]:
    order: List[str] = ["requirements.txt"]
    if include_full:
        order += ["requirements-dev.txt", "requirements-doctr.txt"]
    else:
        order += ["requirements-dev.txt"]
    files = [repo_root / name for name in order if (repo_root / name).exists()]
    return files


def lock_files(repo_root: Path, include_full: bool) -> List[Path]:
    names: List[str] = [
        "requirements.lock",
        "requirements.txt.lock",
    ]
    if include_full:
        names += [
            "requirements-dev.lock",
            "requirements-dev.txt.lock",
            "requirements-doctr.lock",
            "requirements-doctr.txt.lock",
        ]
    else:
        names += ["requirements-dev.lock", "requirements-dev.txt.lock"]
    locks = [repo_root / name for name in names if (repo_root / name).exists()]
    # fall back to workspace-level locks to avoid floating installs
    workspace_lock = ROOT / (
        "requirements.workspace.lock"
        if include_full
        else "requirements.workspace.min.lock"
    )
    if workspace_lock.exists():
        locks.append(workspace_lock)
    return locks


def default_venv_path(repo_root: Path, repo_name: str, explicit: str | None) -> Path:
    if explicit:
        return ROOT / explicit
    # prefer per-repo named venv to aid search/indexing
    candidate = repo_root / f".venv-{repo_name}"
    return candidate


def sync_repo(
    uv_bin: Path,
    repo_name: str,
    _repo_root: Path,
    venv_path: Path,
    reqs: List[Path],
    perform_check: bool,
    mode: str,
    locks: List[Path],
) -> Tuple[str, bool]:
    venv_path.parent.mkdir(parents=True, exist_ok=True)
    _run_command([str(uv_bin), "venv", str(venv_path)])
    if not reqs:
        print(f"[sync-venvs] {repo_name}: no requirements files; skipped installs")
        return (repo_name, True)
    chosen_mode = mode
    if mode == "auto":
        chosen_mode = "sync" if locks else "install"
    cmd = [
        str(uv_bin),
        "pip",
        "install" if chosen_mode == "install" else "sync",
        "--python",
        str(venv_path / "bin" / "python"),
    ]
    if chosen_mode == "install":
        cmd.append("--upgrade")
        for r in reqs:
            cmd.extend(["-r", str(r)])
    else:
        sources = locks if locks else reqs
        cmd += [str(r) for r in sources]
    print(
        f"[sync-venvs] {repo_name}: mode={chosen_mode} sources={[p.name for p in (locks if chosen_mode=='sync' else reqs)]}",
    )
    _run_command(cmd)
    if perform_check:
        check_cmd = [
            str(uv_bin),
            "pip",
            "check",
            "--python",
            str(venv_path / "bin" / "python"),
        ]
        result = _run_command(check_cmd, capture_output=True, text=True)
        ok = result.returncode == 0
        status = "ok" if ok else "issues"
        print(f"[sync-venvs] {repo_name}: dependency check -> {status}")
        if not ok:
            sys.stdout.write(result.stdout)
            sys.stderr.write(result.stderr)
        return (repo_name, ok)
    return (repo_name, True)


def target_repos(manifest: dict, names: Iterable[str] | None) -> List[dict]:
    repos = manifest.get("repos", [])
    selected = []
    for entry in repos:
        if names and entry.get("name") not in names:
            continue
        if entry.get("language") != "python":
            continue
        selected.append(entry)
    return selected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", action="append", help="Limit to repo name (can be repeated)"
    )
    parser.add_argument(
        "--all", action="store_true", help="Process all Python repos (default)"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Include optional/extra requirement files (dev/doctr/etc.)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run `uv pip check` after sync to flag version mismatches",
    )
    parser.add_argument(
        "--mode",
        choices=["install", "sync", "auto"],
        default="auto",
        help="auto (default): prefer sync when lockfiles exist; "
        "install: resolve transitive deps (uv pip install --upgrade -r ...); "
        "sync: expect fully pinned requirement files (uv pip sync ...)",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Number of repos to process in parallel (default: 1)",
    )
    args = parser.parse_args(argv)

    manifest = load_manifest()
    names = set(args.repo or [])
    repos = target_repos(manifest, names if not args.all else None)
    if not repos:
        print("[sync-venvs] No Python repos matched selection.", file=sys.stderr)
        return 1

    uv_bin = ensure_uv()
    failures: List[str] = []

    def _task(entry: dict) -> tuple[str, bool]:
        name = entry["name"]
        repo_root = ROOT / entry["path"]
        venv_path = default_venv_path(repo_root, name, entry.get("venv"))
        reqs = requirement_files(repo_root, include_full=args.full)
        locks = lock_files(repo_root, include_full=args.full)
        print(
            f"[sync-venvs] syncing {name} -> {venv_path} using {', '.join(r.name for r in reqs) or 'no reqs'}"
        )
        _, ok = sync_repo(
            uv_bin, name, repo_root, venv_path, reqs, args.check, args.mode, locks
        )
        return name, ok

    jobs = max(1, args.jobs)
    if jobs == 1:
        results = [_task(entry) for entry in repos]
    else:
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            results = list(pool.map(_task, repos))

    for name, ok in results:
        if not ok:
            failures.append(name)

    if failures:
        print(
            f"[sync-venvs] completed with issues in: {', '.join(sorted(failures))}",
            file=sys.stderr,
        )
        return 1

    print("[sync-venvs] all selected repos synced successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
