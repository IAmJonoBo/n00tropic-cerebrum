#!/usr/bin/env python3
"""
Fail if new floating Python requirements are introduced outside the allowlist.
Floating = any specifier without an explicit == pin.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST_PATH = ROOT / "automation" / "requirements-unpinned-allowlist.json"
WORKSPACE_MANIFEST = ROOT / "automation" / "workspace.manifest.json"

COMMENT_OR_INCLUDE = re.compile(r"^(#|--|-r)")


def load_allowlist() -> dict[str, set[str]]:
    if not ALLOWLIST_PATH.exists():
        return {}
    data = json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    files = data.get("files", {})
    return {k: set(v) for k, v in files.items()}


def target_req_files() -> list[Path]:
    paths = {Path(".")}
    if WORKSPACE_MANIFEST.exists():
        manifest = json.loads(WORKSPACE_MANIFEST.read_text(encoding="utf-8"))
        for repo in manifest.get("repos", []):
            if repo.get("language") == "python":
                paths.add(Path(repo["path"]))
    req_files: list[Path] = []
    ignore_dirs = {
        ".venv",
        ".venv-frontiers",
        ".venv-workspace",
        ".git",
        "node_modules",
        "dist",
        "build",
        "artifacts",
        ".uv-cache",
        ".cache",
        "env",
        "__pycache__",
        "DashboardApp.app",
    }
    for base in paths:
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
            for filename in filenames:
                if not filename.startswith("requirements") or not filename.endswith(
                    ".txt"
                ):
                    continue
                file = Path(dirpath) / filename
                req_files.append(file)
    return req_files


def line_is_floating(line: str) -> bool:
    base = line.split(";", 1)[0].strip()
    return "==" not in base


def main() -> int:
    allowlist = load_allowlist()
    offenders: list[tuple[str, str]] = []
    for req_file in target_req_files():
        rel = req_file.as_posix().lstrip("./")
        allowed_lines = allowlist.get(rel, set())
        for raw in req_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or COMMENT_OR_INCLUDE.match(line):
                continue
            if not line_is_floating(line):
                continue
            if line in allowed_lines:
                continue
            offenders.append((rel, line))
    if offenders:
        print("[lint-unpinned-reqs] floating requirements not in allowlist:")
        for rel, line in offenders:
            print(f"  {rel}: {line}")
        print(
            "Add pins or update automation/requirements-unpinned-allowlist.json if truly intentional."
        )
        return 1
    print("[lint-unpinned-reqs] OK (no new floating requirements).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
