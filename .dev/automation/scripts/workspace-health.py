#!/usr/bin/env python3
"""Report and optionally repair workspace/submodule health for n00tropic-cerebrum."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[3]


@dataclass
class RepoStatus:
    name: str
    path: Path
    clean: bool
    ahead: int
    behind: int
    dirty_lines: List[str]
    branch: str
    upstream: str | None
    head: str

    def summary(self) -> str:
        if self.clean and not self.ahead and not self.behind:
            return "clean"
        parts: List[str] = []
        if not self.clean:
            parts.append("dirty")
        if self.ahead:
            parts.append(f"ahead +{self.ahead}")
        if self.behind:
            parts.append(f"behind -{self.behind}")
        return ", ".join(parts) or "clean"

    def as_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "path": str(self.path),
            "clean": self.clean,
            "ahead": self.ahead,
            "behind": self.behind,
            "branch": self.branch,
            "upstream": self.upstream,
            "head": self.head,
            "dirty": list(self.dirty_lines),
        }


def run_git(args: List[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def parse_status(output: str) -> Dict[str, object]:
    dirty: List[str] = []
    ahead = behind = 0
    branch = "unknown"
    upstream = None
    for line in output.splitlines():
        if line.startswith("# branch.ab"):
            # format: # branch.ab +<ahead> -<behind>
            try:
                _, _, payload = line.partition("ab ")
                ahead_str, behind_str = payload.split()
                ahead = int(ahead_str)
                behind = int(behind_str)
            except ValueError:
                continue
        elif line.startswith("# branch.head"):
            branch = line.split()[-1]
        elif line.startswith("# branch.upstream"):
            upstream = line.split()[-1]
        elif not line.startswith("#"):
            dirty.append(line)
    return {
        "dirty": dirty,
        "ahead": ahead,
        "behind": behind,
        "branch": branch,
        "upstream": upstream,
    }


def collect_repo_status(name: str, path: Path) -> RepoStatus:
    status = run_git(["status", "--porcelain=2", "--branch"], path)
    data = parse_status(status.stdout)
    head = run_git(["rev-parse", "--short", "HEAD"], path).stdout.strip()
    return RepoStatus(
        name=name,
        path=path,
        clean=not data["dirty"],
        ahead=data["ahead"],
        behind=data["behind"],
        dirty_lines=list(data["dirty"]),
        branch=data["branch"],
        upstream=data["upstream"],
        head=head,
    )


def parse_gitmodules(path: Path) -> List[Dict[str, str]]:
    modules: List[Dict[str, str]] = []
    if not path.exists():
        return modules
    current: Dict[str, str] | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw.startswith("[submodule"):
            name = raw.split('"')[1]
            current = {"name": name}
            modules.append(current)
        elif "=" in raw and current is not None:
            key, value = [item.strip() for item in raw.split("=", maxsplit=1)]
            current[key] = value
    return modules


def autofix_workspace(root: Path) -> List[str]:
    commands = [
        ["git", "submodule", "sync", "--recursive"],
        ["git", "submodule", "update", "--init", "--recursive"],
    ]
    logs: List[str] = []
    for cmd in commands:
        result = subprocess.run(
            cmd, cwd=root, text=True, capture_output=True, check=False
        )
        if result.stdout:
            logs.append(result.stdout.strip())
        if result.stderr:
            logs.append(result.stderr.strip())
    return [line for line in logs if line]


def build_report(args: argparse.Namespace) -> Dict[str, object]:
    if args.autofix:
        autofix_workspace(ROOT)
    modules = parse_gitmodules(ROOT / ".gitmodules")
    report: Dict[str, object] = {
        "root": collect_repo_status("workspace", ROOT),
        "submodules": [],
    }
    sub_statuses: List[RepoStatus] = []
    for module in modules:
        path = ROOT / module.get("path", module["name"])
        if not path.exists():
            continue
        sub_statuses.append(collect_repo_status(module["name"], path))
    report["submodules"] = sub_statuses
    return report


def emit(report: Dict[str, object], json_mode: bool) -> None:
    root_status: RepoStatus = report["root"]
    subs: List[RepoStatus] = report["submodules"]
    dirty_subs = [repo for repo in subs if not repo.clean or repo.ahead or repo.behind]
    print(
        f"workspace: {root_status.summary()} (branch {root_status.branch}, HEAD {root_status.head})"
    )
    if root_status.dirty_lines:
        print("  root changes:")
        for line in root_status.dirty_lines[:10]:
            print(f"    {line}")
    if dirty_subs:
        print(f"submodules needing attention: {len(dirty_subs)}/{len(subs)}")
        for repo in dirty_subs:
            print(
                f"- {repo.name}: {repo.summary()} (branch {repo.branch}, HEAD {repo.head})"
            )
            for line in repo.dirty_lines[:5]:
                print(f"    {line}")
    else:
        print("all submodules clean")
    if json_mode:
        payload = {
            "root": root_status.as_dict(),
            "submodules": [repo.as_dict() for repo in subs],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Workspace health checker for the federated polyrepo."
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON payload after human summary."
    )
    parser.add_argument(
        "--autofix",
        action="store_true",
        help="Sync & init submodules before reporting.",
    )
    args = parser.parse_args()
    report = build_report(args)
    emit(report, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
