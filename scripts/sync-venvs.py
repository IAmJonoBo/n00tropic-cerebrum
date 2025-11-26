#!/usr/bin/env python3
"""
Sync per-repo Python virtual environments using workspace manifest.

Defaults:
  - Reads automation/workspace.manifest.json
  - Creates venv at manifest["venv"] (fallback: <repo>/.venv-<name> or .venv)
  - Installs requirements in priority order:
      requirements.txt, requirements-dev.txt, requirements-doctr.txt (if present)
  - Uses uv for reproducible sync; installs uv if missing.

Examples:
  python3 scripts/sync-venvs.py --all --check
  python3 scripts/sync-venvs.py --repo n00t --full --check
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple

import argparse
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "automation" / "workspace.manifest.json"


def ensure_uv() -> Path:
    uv = shutil.which("uv")
    if uv:
        return Path(uv)
    install_cmd = (
        "curl -LsSf https://astral.sh/uv/install.sh | sh"
        if shutil.which("curl")
        else "wget -qO- https://astral.sh/uv/install.sh | sh"
    )
    print("[sync-venvs] uv not found; installing via Astral script…", file=sys.stderr)
    subprocess.run(install_cmd, shell=True, check=True)
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


def default_venv_path(repo_root: Path, repo_name: str, explicit: str | None) -> Path:
    if explicit:
        return ROOT / explicit
    # prefer per-repo named venv to aid search/indexing
    candidate = repo_root / f".venv-{repo_name}"
    return candidate


def sync_repo(
    uv_bin: Path,
    repo_name: str,
    repo_root: Path,
    venv_path: Path,
    reqs: List[Path],
    perform_check: bool,
) -> Tuple[str, bool]:
    venv_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([uv_bin, "venv", str(venv_path)], check=True)
    if not reqs:
        print(f"[sync-venvs] {repo_name}: no requirements files; skipped installs")
        return (repo_name, True)
    cmd = [
        uv_bin,
        "pip",
        "sync",
        "--python",
        str(venv_path / "bin" / "python"),
        *[str(r) for r in reqs],
    ]
    subprocess.run(cmd, check=True)
    if perform_check:
        check_cmd = [
            uv_bin,
            "pip",
            "check",
            "--python",
            str(venv_path / "bin" / "python"),
        ]
        result = subprocess.run(check_cmd, capture_output=True, text=True)
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
    args = parser.parse_args(argv)

    manifest = load_manifest()
    names = set(args.repo or [])
    repos = target_repos(manifest, names if not args.all else None)
    if not repos:
        print("[sync-venvs] No Python repos matched selection.", file=sys.stderr)
        return 1

    uv_bin = ensure_uv()
    failures: List[str] = []

    for entry in repos:
        name = entry["name"]
        repo_root = ROOT / entry["path"]
        venv_path = default_venv_path(repo_root, name, entry.get("venv"))
        reqs = requirement_files(repo_root, include_full=args.full)
        print(
            f"[sync-venvs] syncing {name} -> {venv_path} using {', '.join(r.name for r in reqs) or 'no reqs'}"
        )
        try:
            _, ok = sync_repo(uv_bin, name, repo_root, venv_path, reqs, args.check)
            if not ok:
                failures.append(name)
        except subprocess.CalledProcessError as exc:
            failures.append(name)
            print(f"[sync-venvs] {name}: failed ({exc})", file=sys.stderr)

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
