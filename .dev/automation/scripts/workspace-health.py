#!/usr/bin/env python3
"""Report workspace + submodule health, with optional repair hooks."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess  # nosec B404 - toolchain commands are workspace-managed
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


def _resolve_command(cmd: Sequence[str]) -> List[str]:
    if not cmd:
        raise ValueError("Command must include at least one argument")
    executable = shutil.which(cmd[0])
    if executable:
        return [executable, *cmd[1:]]
    return list(cmd)


def _run_process(
    cmd: Sequence[str],
    *,
    cwd: Path,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    resolved = _resolve_command(cmd)
    return subprocess.run(  # nosec B603 - commands resolved from curated allowlist
        resolved,
        cwd=cwd,
        text=True,
        capture_output=capture_output,
        check=False,
    )


def run_git(args: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return _run_process(["git", *args], cwd=cwd)


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
    completed = _run_process(cmd, cwd=cwd)
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
        try:
            command = shlex.split(raw)
        except ValueError as exc:  # pragma: no cover - defensive guard
            logs.append(f"Failed to parse repo command '{raw}': {exc}")
            continue
        if not command:
            logs.append(f"Repo command '{entry}' is empty after parsing")
            continue
        logs.extend(_run_command(command, repo_path))
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


def _load_payload(raw_payload: str) -> Dict[str, object] | None:
    try:
        return json.loads(raw_payload)
    except json.JSONDecodeError:
        return None


def _parse_payload_overrides(payload: Dict[str, object]) -> Dict[str, object]:
    payload_input = payload.get("input")
    if isinstance(payload_input, str):
        try:
            return json.loads(payload_input)
        except json.JSONDecodeError:
            return {}
    if isinstance(payload_input, dict):
        return payload_input  # type: ignore[return-value]
    return {}


def _apply_bool_override(
    args: argparse.Namespace, overrides: Dict[str, object], key: str, attr: str
) -> None:
    if key in overrides and not getattr(args, attr):
        setattr(args, attr, bool(overrides[key]))


def apply_payload_overrides(args: argparse.Namespace) -> argparse.Namespace:
    raw_payload = os.environ.get("CAPABILITY_PAYLOAD") or os.environ.get(
        "CAPABILITY_INPUT"
    )
    if not raw_payload:
        return args
    payload = _load_payload(raw_payload)
    if not payload:
        return args
    overrides = _parse_payload_overrides(payload)
    if payload.get("output") and not args.json_path:
        args.json_path = str(payload["output"])
    if payload.get("check"):
        args.strict = True
    if overrides:
        _apply_bool_override(args, overrides, "cleanUntracked", "clean_untracked")
        _apply_bool_override(args, overrides, "syncSubmodules", "sync_submodules")
        _apply_bool_override(args, overrides, "publishArtifact", "publish_artifact")
        _apply_bool_override(args, overrides, "strict", "strict")
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


def _collect_dirty_submodules(subs: Sequence[RepoStatus]) -> List[RepoStatus]:
    return [
        repo
        for repo in subs
        if repo.tracked_lines or repo.untracked_lines or repo.ahead or repo.behind
    ]


def _print_repo_lines(header: str, lines: Sequence[str], limit: int) -> None:
    if not lines:
        return
    print(header)
    for line in lines[:limit]:
        print(f"    {line}")


def _print_submodule_details(dirty_subs: Sequence[RepoStatus], total: int) -> None:
    if not dirty_subs:
        print("all submodules clean")
        return
    print(f"submodules needing attention: {len(dirty_subs)}/{total}")
    for repo in dirty_subs:
        print(
            f"- {repo.name}: {repo.summary()} (branch {repo.branch}, HEAD {repo.head})"
        )
        _print_repo_lines("    tracked:", repo.tracked_lines, 3)
        _print_repo_lines("    untracked:", repo.untracked_lines, 3)


def _build_payload(
    root_status: RepoStatus, subs: Sequence[RepoStatus], logs: List[str]
) -> Dict[str, object]:
    return {
        "root": root_status.as_dict(),
        "submodules": [repo.as_dict() for repo in subs],
        "logs": logs,
    }


def _determine_exit_code(
    root_status: RepoStatus, dirty_subs: Sequence[RepoStatus], args: argparse.Namespace
) -> int:
    strict_root = args.strict_root or args.strict
    strict_subs = args.strict_submodules or args.strict
    if strict_root and (
        root_status.tracked_lines
        or root_status.untracked_lines
        or root_status.ahead
        or root_status.behind
    ):
        return 1
    if strict_subs and dirty_subs:
        return 1
    return 0


def emit(report: Dict[str, object], args: argparse.Namespace) -> int:
    root_status: RepoStatus = report["root"]
    subs: List[RepoStatus] = report["submodules"]
    logs: List[str] = report["logs"]
    dirty_subs = _collect_dirty_submodules(subs)

    print(
        f"workspace: {root_status.summary()} (branch {root_status.branch}, HEAD {root_status.head})"
    )
    _print_repo_lines("  tracked changes:", root_status.tracked_lines, 10)
    _print_repo_lines("  untracked files:", root_status.untracked_lines, 10)
    if logs:
        print("helper logs:")
        for line in logs:
            print(f"  {line}")
    _print_submodule_details(dirty_subs, len(subs))

    payload = _build_payload(root_status, subs, logs)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))

    if args.publish_artifact and not args.json_path:
        args.json_path = str(DEFAULT_ARTIFACT_PATH)
    publish_json_artifact(payload, args)
    return _determine_exit_code(root_status, dirty_subs, args)


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
        help="Run custom command inside a repo (format repo:command). Commands are tokenized with shlex, so shell features like && are not supported. May repeat.",
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
