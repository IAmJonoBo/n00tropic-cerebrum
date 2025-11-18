#!/usr/bin/env python3
"""Report workspace + submodule health, with optional repair hooks."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

DEFAULT_ARTIFACT_PATH = ROOT / "artifacts" / "workspace-health.json"


@dataclass
class RepoStatus:
    name: str
    path: Path
    clean: bool
    ahead: int
    behind: int
    dirty_lines: List[str]
    tracked_lines: List[str]
    untracked_lines: List[str]
    branch: str
    upstream: str | None
    head: str

    def summary(self) -> str:
        parts: List[str] = []
        if self.tracked_lines or self.untracked_lines:
            dirty_bits: List[str] = []
            if self.tracked_lines:
                dirty_bits.append(f"tracked {len(self.tracked_lines)}")
            if self.untracked_lines:
                dirty_bits.append(f"untracked {len(self.untracked_lines)}")
            parts.append(", ".join(dirty_bits))
        else:
            parts.append("clean")
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
            "tracked": list(self.tracked_lines),
            "untracked": list(self.untracked_lines),
        }


def run_git(args: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, text=True, capture_output=True, check=False
    )


def parse_status(output: str) -> Dict[str, object]:
    dirty: List[str] = []
    tracked: List[str] = []
    untracked: List[str] = []
    ahead = behind = 0
    branch = "unknown"
    upstream = None
    for line in output.splitlines():
        if line.startswith("# branch.ab"):
            try:
                _, _, payload = line.partition("ab ")
                ahead_token, behind_token = payload.split()
                ahead = int(ahead_token)
                behind = int(behind_token)
            except ValueError:
                continue
        elif line.startswith("# branch.head"):
            branch = line.split()[-1]
        elif line.startswith("# branch.upstream"):
            upstream = line.split()[-1]
        elif line.startswith("? "):
            dirty.append(line)
            untracked.append(line)
        elif line.startswith("! "):
            continue
        elif not line.startswith("#"):
            dirty.append(line)
            tracked.append(line)
    return {
        "dirty": dirty,
        "tracked": tracked,
        "untracked": untracked,
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
        clean=not data["tracked"] and not data["untracked"],
        ahead=data["ahead"],
        behind=data["behind"],
        dirty_lines=list(data["dirty"]),
        tracked_lines=list(data["tracked"]),
        untracked_lines=list(data["untracked"]),
        branch=data["branch"],
        upstream=data["upstream"],
        head=head or "HEAD",
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


def _run_command(cmd: Sequence[str], cwd: Path) -> List[str]:
    completed = subprocess.run(
        cmd, cwd=cwd, text=True, capture_output=True, check=False
    )
    logs: List[str] = []
    if completed.stdout:
        logs.append(completed.stdout.strip())
    if completed.stderr:
        logs.append(completed.stderr.strip())
    if completed.returncode != 0:
        logs.append(f"Command {' '.join(cmd)} exited with {completed.returncode}")
    return [line for line in logs if line]


def sync_submodules(root: Path) -> List[str]:
    logs: List[str] = []
    logs.extend(_run_command(["git", "submodule", "sync", "--recursive"], root))
    logs.extend(
        _run_command(["git", "submodule", "update", "--init", "--recursive"], root)
    )
    return logs


def sync_trunk_configs(root: Path) -> List[str]:
    script = root / ".dev" / "automation" / "scripts" / "sync-trunk.py"
    if not script.exists():
        return [f"sync-trunk script missing at {script}"]
    return _run_command(["python3", str(script), "--pull"], root)


def run_meta_check(root: Path) -> List[str]:
    script = root / ".dev" / "automation" / "scripts" / "meta-check.sh"
    if not script.exists():
        return [f"meta-check script missing at {script}"]
    return _run_command(["bash", str(script)], root)


def run_repo_commands(
    entries: Sequence[str], modules: List[Dict[str, str]]
) -> List[str]:
    logs: List[str] = []
    for entry in entries:
        if ":" not in entry:
            logs.append(f"Invalid repo-cmd '{entry}'. Use repo:command format.")
            continue
        repo_name, raw = entry.split(":", 1)
        repo_path = next(
            (
                ROOT / mod.get("path", mod["name"])
                for mod in modules
                if mod.get("name") == repo_name
            ),
            None,
        )
        if repo_path is None or not repo_path.exists():
            logs.append(f"Repo '{repo_name}' not found for repo-cmd")
            continue
        logs.extend(_run_command(["bash", "-lc", raw], repo_path))
    return logs


def build_report(args: argparse.Namespace) -> Dict[str, object]:
    modules = parse_gitmodules(ROOT / ".gitmodules")
    logs: List[str] = []
    if args.fix_all or args.sync_submodules:
        logs.extend(sync_submodules(ROOT))
    if args.fix_all or args.sync_trunk:
        logs.extend(sync_trunk_configs(ROOT))
    if args.run_meta_check:
        logs.extend(run_meta_check(ROOT))
    if args.repo_cmd:
        logs.extend(run_repo_commands(args.repo_cmd, modules))
    root_status, submodule_statuses = snapshot_workspace(modules)
    if args.clean_untracked:
        logs.extend(clean_untracked_entries([root_status, *submodule_statuses]))
        root_status, submodule_statuses = snapshot_workspace(modules)
    report: Dict[str, object] = {
        "root": root_status,
        "submodules": submodule_statuses,
        "logs": logs,
    }
    return report


def snapshot_workspace(
    modules: List[Dict[str, str]],
) -> Tuple[RepoStatus, List[RepoStatus]]:
    root_status = collect_repo_status("workspace", ROOT)
    submodule_statuses: List[RepoStatus] = []
    for module in modules:
        module_path = ROOT / module.get("path", module["name"])
        if module_path.exists():
            submodule_statuses.append(collect_repo_status(module["name"], module_path))
    return root_status, submodule_statuses


def clean_untracked_entries(repos: Iterable[RepoStatus]) -> List[str]:
    logs: List[str] = []
    ran_action = False
    for repo in repos:
        if repo.tracked_lines or not repo.untracked_lines:
            continue
        ran_action = True
        logs.append(
            f"[clean] git clean -fd in {repo.name} ({len(repo.untracked_lines)} entries)"
        )
        logs.extend(_run_command(["git", "clean", "-fd"], repo.path))
    if not ran_action:
        return ["[clean] no safe untracked entries to remove"]
    return logs


def apply_payload_overrides(args: argparse.Namespace) -> argparse.Namespace:
    raw_payload = os.environ.get("CAPABILITY_PAYLOAD") or os.environ.get(
        "CAPABILITY_INPUT"
    )
    if not raw_payload:
        return args
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return args
    overrides: Dict[str, object] = {}
    payload_input = payload.get("input")
    if isinstance(payload_input, str):
        try:
            overrides = json.loads(payload_input)
        except json.JSONDecodeError:
            overrides = {}
    elif isinstance(payload_input, dict):
        overrides = payload_input  # type: ignore[assignment]
    if payload.get("output") and not args.json_path:
        args.json_path = str(payload["output"])
    if payload.get("check"):
        args.strict = True
    if isinstance(overrides, dict):
        if "cleanUntracked" in overrides and not args.clean_untracked:
            args.clean_untracked = bool(overrides["cleanUntracked"])
        if "syncSubmodules" in overrides and not args.sync_submodules:
            args.sync_submodules = bool(overrides["syncSubmodules"])
        if "publishArtifact" in overrides and not args.publish_artifact:
            args.publish_artifact = bool(overrides["publishArtifact"])
        if "strict" in overrides and not args.strict:
            args.strict = bool(overrides["strict"])
    return args


def publish_json_artifact(payload: Dict[str, object], args: argparse.Namespace) -> None:
    if not args.json_path:
        return
    destination = Path(str(args.json_path)).expanduser()
    if destination.is_dir():
        destination = destination / "workspace-health.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def emit(report: Dict[str, object], args: argparse.Namespace) -> int:
    root_status: RepoStatus = report["root"]
    subs: List[RepoStatus] = report["submodules"]
    dirty_subs = [
        repo
        for repo in subs
        if repo.tracked_lines or repo.untracked_lines or repo.ahead or repo.behind
    ]

    print(
        f"workspace: {root_status.summary()} (branch {root_status.branch}, HEAD {root_status.head})"
    )
    if root_status.tracked_lines:
        print("  tracked changes:")
        for line in root_status.tracked_lines[:10]:
            print(f"    {line}")
    if root_status.untracked_lines:
        print("  untracked files:")
        for line in root_status.untracked_lines[:10]:
            print(f"    {line}")
    if report["logs"]:
        print("helper logs:")
        for line in report["logs"]:
            print(f"  {line}")
    if dirty_subs:
        print(f"submodules needing attention: {len(dirty_subs)}/{len(subs)}")
        for repo in dirty_subs:
            print(
                f"- {repo.name}: {repo.summary()} (branch {repo.branch}, HEAD {repo.head})"
            )
            if repo.tracked_lines:
                print("    tracked:")
                for line in repo.tracked_lines[:3]:
                    print(f"      {line}")
            if repo.untracked_lines:
                print("    untracked:")
                for line in repo.untracked_lines[:3]:
                    print(f"      {line}")
    else:
        print("all submodules clean")

    payload = {
        "root": root_status.as_dict(),
        "submodules": [repo.as_dict() for repo in subs],
        "logs": report["logs"],
    }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))

    if args.publish_artifact and not args.json_path:
        args.json_path = str(DEFAULT_ARTIFACT_PATH)
    publish_json_artifact(payload, args)

    strict_root = args.strict_root or args.strict
    strict_subs = args.strict_submodules or args.strict
    exit_code = 0
    if strict_root and (
        root_status.tracked_lines
        or root_status.untracked_lines
        or root_status.ahead
        or root_status.behind
    ):
        exit_code = 1
    if strict_subs and dirty_subs:
        exit_code = 1
    return exit_code


def main() -> int:
    from observability import initialize_tracing

    initialize_tracing("workspace-health")
    parser = argparse.ArgumentParser(
        description="Workspace health checker for the federated polyrepo."
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON payload after human summary."
    )
    parser.add_argument(
        "--sync-submodules",
        action="store_true",
        help="Sync & init submodules before reporting.",
    )
    parser.add_argument(
        "--sync-trunk",
        action="store_true",
        help="Run sync-trunk.py --pull before reporting.",
    )
    parser.add_argument(
        "--run-meta-check",
        action="store_true",
        help="Invoke meta-check automation before reporting.",
    )
    parser.add_argument(
        "--repo-cmd",
        action="append",
        default=[],
        help="Run custom command inside a repo (format repo:command). May repeat.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when root/submodules are dirty or diverged.",
    )
    parser.add_argument(
        "--strict-root",
        action="store_true",
        help="Exit non-zero when workspace root is dirty or diverged.",
    )
    parser.add_argument(
        "--strict-submodules",
        action="store_true",
        help="Exit non-zero when any submodule is dirty or diverged.",
    )
    parser.add_argument(
        "--fix-all",
        action="store_true",
        help="Run all helper hooks (submodule + trunk sync) before reporting.",
    )
    parser.add_argument("--autofix", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--clean-untracked",
        action="store_true",
        help="Run git clean -fd for repos that only have untracked files.",
    )
    parser.add_argument(
        "--json-path",
        help="Write the JSON payload to a specific path (defaults to artifacts when --publish-artifact is set).",
    )
    parser.add_argument(
        "--publish-artifact",
        action="store_true",
        help="Persist workspace-health.json under artifacts/ for AI/agent consumers.",
    )
    args = parser.parse_args()
    args = apply_payload_overrides(args)
    if args.autofix:
        args.sync_submodules = True
    report = build_report(args)
    return emit(report, args)


if __name__ == "__main__":
    raise SystemExit(main())
