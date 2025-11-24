#!/usr/bin/env python3
"""Workspace orchestration CLI for the n00tropic polyrepo."""

from __future__ import annotations

import argparse
import json
import os
import subprocess  # nosec B404 - trusted workspace commands only
import sys
from pathlib import Path
from shutil import which
from typing import Iterable, List, Optional, Tuple

from observability import initialize_tracing

WORKSPACE_ROOT = Path(__file__).resolve().parent
ORG_ROOT = WORKSPACE_ROOT.parent
SCRIPTS_ROOT = ORG_ROOT / ".dev" / "automation" / "scripts"
TRUNK_TIMEOUT = int(os.environ.get("TRUNK_UPGRADE_TIMEOUT", "600"))
GIT_BIN = which("git") or "git"
if not GIT_BIN:
    raise SystemExit("git executable not found in PATH")

SUBREPO_CONTEXT = {
    "workspace": {
        "path": WORKSPACE_ROOT,
        "language": "mixed",
        "pkg": "pnpm",
        "venv": WORKSPACE_ROOT / ".venv-workspace",
        "cli": "python3 cli.py",
        "tooling": WORKSPACE_ROOT / "tooling",
        "scripts_dir": WORKSPACE_ROOT / ".dev" / "automation" / "scripts",
    },
    "n00-cortex": {
        "path": WORKSPACE_ROOT / "n00-cortex",
        "language": "python",
        "pkg": "pnpm",
        "venv": WORKSPACE_ROOT / "n00-cortex" / ".venv",
        "cli": "python3 cli/main.py",
        "tooling": WORKSPACE_ROOT / "n00-cortex" / "tooling",
        "scripts_dir": WORKSPACE_ROOT
        / "n00-cortex"
        / ".dev"
        / "n00-cortex"
        / "scripts",
    },
    "n00-dashboard": {
        "path": WORKSPACE_ROOT / "n00-dashboard",
        "language": "node",
        "pkg": "pnpm",
        "venv": None,
        "cli": "pnpm exec ts-node cli/index.ts",
        "tooling": WORKSPACE_ROOT / "n00-dashboard" / "tooling",
        "scripts_dir": WORKSPACE_ROOT
        / "n00-dashboard"
        / ".dev"
        / "n00-dashboard"
        / "scripts",
    },
    "n00-frontiers": {
        "path": WORKSPACE_ROOT / "n00-frontiers",
        "language": "python",
        "pkg": "pnpm",
        "venv": WORKSPACE_ROOT / "n00-frontiers" / ".venv-frontiers",
        "cli": "python3 cli/main.py",
        "tooling": WORKSPACE_ROOT / "n00-frontiers" / "tooling",
        "scripts_dir": WORKSPACE_ROOT
        / "n00-frontiers"
        / ".dev"
        / "n00-frontiers"
        / "scripts",
    },
    "n00-horizons": {
        "path": WORKSPACE_ROOT / "n00-horizons",
        "language": "python",
        "pkg": "pnpm",
        "venv": WORKSPACE_ROOT / "n00-horizons" / ".venv-horizons",
        "cli": "python3 cli/main.py",
        "tooling": WORKSPACE_ROOT / "n00-horizons" / "tooling",
        "scripts_dir": WORKSPACE_ROOT
        / "n00-horizons"
        / ".dev"
        / "n00-horizons"
        / "scripts",
    },
    "n00-school": {
        "path": WORKSPACE_ROOT / "n00-school",
        "language": "python",
        "pkg": "pnpm",
        "venv": WORKSPACE_ROOT / "n00-school" / ".venv-school",
        "cli": "python3 cli/main.py",
        "tooling": WORKSPACE_ROOT / "n00-school" / "tooling",
        "scripts_dir": WORKSPACE_ROOT
        / "n00-school"
        / ".dev"
        / "n00-school"
        / "scripts",
    },
    "n00clear-fusion": {
        "path": WORKSPACE_ROOT / "n00clear-fusion",
        "language": "python",
        "pkg": "pnpm",
        "venv": WORKSPACE_ROOT / "n00clear-fusion" / ".venv-fusion",
        "cli": "python3 cli/main.py",
        "tooling": WORKSPACE_ROOT / "n00clear-fusion" / "tooling",
        "scripts_dir": WORKSPACE_ROOT
        / "n00clear-fusion"
        / ".dev"
        / "n00clear-fusion"
        / "scripts",
    },
    "n00plicate": {
        "path": WORKSPACE_ROOT / "n00plicate",
        "language": "node",
        "pkg": "pnpm",
        "venv": None,
        "cli": "pnpm exec ts-node cli/index.ts",
        "tooling": WORKSPACE_ROOT / "n00plicate" / "tooling",
        "scripts_dir": WORKSPACE_ROOT
        / "n00plicate"
        / ".dev"
        / "n00plicate"
        / "scripts",
    },
    "n00menon": {
        "path": WORKSPACE_ROOT / "n00menon",
        "language": "node",
        "pkg": "pnpm",
        "venv": None,
        "cli": "pnpm -C n00menon run validate",
        "tooling": None,
        "scripts_dir": WORKSPACE_ROOT / "scripts",
    },
    "n00t": {
        "path": WORKSPACE_ROOT / "n00t",
        "language": "node",
        "pkg": "pnpm",
        "venv": None,
        "cli": "pnpm exec ts-node cli/index.ts",
        "tooling": WORKSPACE_ROOT / "n00t" / "tooling",
        "scripts_dir": WORKSPACE_ROOT / "n00t" / ".dev" / "n00t" / "scripts",
    },
    "n00tropic": {
        "path": WORKSPACE_ROOT / "n00tropic",
        "language": "python",
        "pkg": "pnpm",
        "venv": WORKSPACE_ROOT / "n00tropic" / ".venv",
        "cli": "python3 cli/main.py",
        "tooling": WORKSPACE_ROOT / "n00tropic" / "tooling",
        "scripts_dir": WORKSPACE_ROOT / "n00tropic" / ".dev" / "n00tropic" / "scripts",
    },
}

SUBREPO_MAP = {name: meta["path"] for name, meta in SUBREPO_CONTEXT.items()}


def iter_repos(selected: Optional[Iterable[str]] = None) -> List[Tuple[str, Path]]:
    names = list(selected) if selected else list(SUBREPO_CONTEXT.keys())
    repos: List[Tuple[str, Path]] = []
    for name in names:
        path = SUBREPO_MAP.get(name)
        if not path:
            print(f"[remotes] Unknown repo '{name}' – skipping", file=sys.stderr)
            continue
        repos.append((name, path))
    return repos


def run(
    cmd: List[str],
    cwd: Path,
    *,
    capture_output: bool = False,
    text: bool = True,
    check: bool = True,
    env: Optional[dict] = None,
) -> subprocess.CompletedProcess[str]:
    """Execute trusted workspace commands with consistent subprocess defaults."""

    return subprocess.run(  # nosec B603 - commands are workspace-managed and vetted
        cmd,
        check=check,
        cwd=cwd,
        capture_output=capture_output,
        text=text,
        env=env,
    )


def run_script(script_name: str, *args: str) -> None:
    script_path = SCRIPTS_ROOT / script_name
    if not script_path.exists():
        raise SystemExit(f"Script not found: {script_path}")
    run([str(script_path), *args], cwd=ORG_ROOT)


def run_workspace_script(script_name: str, *args: str) -> None:
    script_path = WORKSPACE_ROOT / ".dev" / "automation" / "scripts" / script_name
    if not script_path.exists():
        raise SystemExit(f"Workspace script not found: {script_path}")
    run([str(script_path), *args], cwd=WORKSPACE_ROOT)


def venv_executable(venv: Path, exe: str) -> Path:
    suffix = "Scripts" if os.name == "nt" else "bin"
    return venv / suffix / exe


def status_report() -> None:
    repos = iter_repos()
    repos.append(("n00tropic_HQ", ORG_ROOT / "n00tropic_HQ"))
    for name, repo_path in repos:
        if not repo_path.exists():
            continue
        result = run(
            [GIT_BIN, "status", "-sb"],
            cwd=repo_path,
            text=True,
            capture_output=True,
            check=False,
        )
        print(f"== {name} ==")
        output = result.stdout.strip()
        print(output or "clean")
        print()


def read_manifest(path: Path) -> None:
    try:
        data = json.loads(path.read_text())
    except Exception as exc:  # pragma: no cover - diagnostic helper
        raise SystemExit(f"Unable to read {path}: {exc}") from exc
    print(json.dumps(data, indent=2))


def load_capabilities_manifest() -> List[dict]:
    manifest_path = WORKSPACE_ROOT / "n00t" / "capabilities" / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(
            f"Capabilities manifest not found at {manifest_path}. Clone the n00t repo or run from the workspace root."
        )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    capabilities = payload.get("capabilities", [])
    if not isinstance(capabilities, list):
        raise SystemExit("n00t capabilities manifest is malformed (expected a list).")
    return capabilities


def list_capabilities(capability_id: Optional[str]) -> None:
    capabilities = load_capabilities_manifest()
    if capability_id:
        for capability in capabilities:
            if capability.get("id") == capability_id:
                print(json.dumps(capability, indent=2))
                return
        raise SystemExit(f"Capability '{capability_id}' not found in n00t manifest.")
    for capability in capabilities:
        summary = capability.get("summary") or capability.get("description") or ""
        print(f"- {capability.get('id')}: {summary}")


def repo_has_git(path: Path) -> bool:
    return (path / ".git").exists() or (path / ".git").is_file()


def ensure_repo_remote(repo: str, path: Path, apply_changes: bool) -> None:
    if not path.exists():
        print(f"[remotes] {repo}: path missing ({path})")
        return
    is_repo = (
        run(
            [GIT_BIN, "rev-parse", "--is-inside-work-tree"],
            cwd=path,
            capture_output=True,
            text=True,
            check=False,
        ).returncode
        == 0
    )
    if not is_repo:
        print(f"[remotes] {repo}: not a git repository, skipping")
        return
    current = run(
        [GIT_BIN, "remote"],
        cwd=path,
        text=True,
        capture_output=True,
        check=False,
    )
    remotes = {line.strip() for line in current.stdout.splitlines() if line.strip()}
    if repo in remotes:
        print(f"[remotes] {repo}: remote already configured")
        return
    origin_url = run(
        [GIT_BIN, "remote", "get-url", "origin"],
        cwd=path,
        text=True,
        capture_output=True,
        check=False,
    )
    if origin_url.returncode != 0:
        print(f"[remotes] {repo}: origin remote missing, cannot synchronise")
        return
    if not apply_changes:
        print(
            f"[remotes] {repo}: remote missing – re-run with --apply to add alias using origin url"
        )
        return
    url = origin_url.stdout.strip()
    run([GIT_BIN, "remote", "add", repo, url], cwd=path)
    print(f"[remotes] {repo}: added remote alias -> {url}")


def run_trunk_upgrade(targets: Optional[Iterable[str]]) -> None:
    if not targets:
        run_script("trunk-upgrade.sh")
        return

    resolved: List[str] = []
    seen = set()
    for name, _ in iter_repos(targets):
        canonical = "n00tropic-cerebrum" if name == "workspace" else name
        if canonical in seen:
            continue
        seen.add(canonical)
        resolved.append(canonical)

    if not resolved:
        print(
            "[trunk] No matching repositories resolved; nothing to do.", file=sys.stderr
        )
        return

    args: List[str] = []
    for name in resolved:
        args.extend(["--repo", name])
    run_script("trunk-upgrade.sh", *args)


PROJECT_COMMAND_SCRIPTS = {
    "capture": "project-capture.sh",
    "sync-github": "project-sync-github.sh",
    "sync-erpnext": "project-sync-erpnext.sh",
}


def handle_docs_sync(_: argparse.Namespace) -> None:
    """Run the superproject docs sync (submodule refresh + n00menon sync/build)."""

    script = SCRIPTS_ROOT / "docs-sync-super.sh"
    if not script.exists():
        raise SystemExit(f"Docs sync script missing: {script}")
    run([str(script)], cwd=ORG_ROOT)


def handle_docs_verify(_: argparse.Namespace) -> None:
    """Run docs verification (Vale/Lychee/attrs) via n00menon and workspace helpers."""

    run_workspace_script("docs-verify.sh")


def handle_docs_lint(_: argparse.Namespace) -> None:
    """Run docs linting (cspell + Vale + Lychee) across workspace."""

    run_workspace_script("docs-lint.sh")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="n00tropic cerebrum orchestrator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("radar", help="Regenerate lifecycle radar artefacts.")

    preflight_parser = subparsers.add_parser(
        "preflight", help="Run batch preflight across registry and/or target docs."
    )
    preflight_parser.add_argument(
        "--paths", nargs="*", default=[], help="Specific metadata paths to include."
    )
    preflight_parser.add_argument(
        "--include-registry",
        action="store_true",
        help="Include every registry-sourced document.",
    )

    subparsers.add_parser(
        "control-panel", help="Regenerate the control panel snapshot."
    )

    subparsers.add_parser(
        "docs-sync",
        help="Refresh docs: update submodules, sync n00menon surfaces, build, format.",
    )
    subparsers.add_parser(
        "docs-verify",
        help="Run fast docs verification (sync check + attrs + link checks).",
    )
    subparsers.add_parser(
        "docs-lint",
        help="Run spell/style/link linting across docs surfaces (workspace + n00menon).",
    )

    autofix_parser = subparsers.add_parser(
        "autofix-links", help="Repair metadata link blocks (default dry-run)."
    )
    autofix_parser.add_argument(
        "--path",
        dest="path_list",
        action="append",
        default=[],
        help="Metadata document to autofix.",
    )
    autofix_parser.add_argument(
        "--all", action="store_true", help="Run across all known documents."
    )
    autofix_parser.add_argument(
        "--apply", action="store_true", help="Persist fixes to disk."
    )

    for name in PROJECT_COMMAND_SCRIPTS:
        cmd_parser = subparsers.add_parser(
            name, help=f"{name.replace('-', ' ').title()} a metadata document."
        )
        cmd_parser.add_argument(
            "--path", required=True, help="Path to the metadata-bearing Markdown file."
        )

    doctor_parser = subparsers.add_parser(
        "doctor", help="Run workspace git doctor checks."
    )
    doctor_parser.add_argument(
        "--strict", action="store_true", help="Fail on advisory findings."
    )
    subparsers.add_parser(
        "repo-context", help="Generate workspace repo context artifact."
    )

    upgrade_parser = subparsers.add_parser(
        "upgrade-tools", help="Check for latest tool versions."
    )
    upgrade_parser.add_argument(
        "--apply", action="store_true", help="Apply suggested upgrades where possible."
    )

    subparsers.add_parser(
        "status", help="Show git status for the workspace and key subrepos."
    )

    manifest_parser = subparsers.add_parser(
        "manifest", help="Pretty-print an artefact JSON/manifest."
    )
    manifest_parser.add_argument("path", help="Path to the JSON file.")

    caps_parser = subparsers.add_parser(
        "capabilities", help="List or inspect n00t capabilities."
    )
    caps_parser.add_argument(
        "--id", help="Show the full manifest entry for a specific capability."
    )

    trunk_parser = subparsers.add_parser(
        "trunk-upgrade",
        help="Run `trunk upgrade` inside every repo with Trunk configuration.",
    )
    trunk_parser.add_argument(
        "--repos",
        nargs="*",
        help="Optional subset of repo names. Defaults to all tracked repos when omitted.",
    )

    trunk_alias_parser = subparsers.add_parser(
        "trunk",
        help="Compatibility shim so `python3 cli.py trunk upgrade` maps to the trunk-upgrade command.",
    )
    trunk_alias_parser.add_argument(
        "subcommand",
        choices=["upgrade"],
        help="Currently only `upgrade` is supported.",
    )
    trunk_alias_parser.add_argument(
        "--repos",
        nargs="*",
        help="Optional subset of repo names to include when running the trunk subcommand.",
    )

    subparsers.add_parser(
        "health-toolchain", help="Check Node/pnpm pins across workspace and subrepos."
    )

    health_runners = subparsers.add_parser(
        "health-runners", help="Check self-hosted runner coverage/labels."
    )
    health_runners.add_argument(
        "--required-labels",
        default=os.environ.get(
            "REQUIRED_RUNNER_LABELS", "self-hosted,linux,x64,pnpm,uv"
        ),
        help="Comma-separated labels that must be present on runners.",
    )
    health_runners.add_argument(
        "--webhook",
        help="Optional Discord webhook to notify (mirrors DISCORD_WEBHOOK env).",
    )

    subparsers.add_parser(
        "health-python-lock", help="Verify uv lock freshness for workspace Python deps."
    )

    normalize_js = subparsers.add_parser(
        "normalize-js", help="Run normalize-workspace-pnpm.sh with pin enforcement."
    )
    normalize_js.add_argument(
        "--allow-mismatch",
        action="store_true",
        help="Allow Node pin mismatch (otherwise fails).",
    )

    remote_parser = subparsers.add_parser(
        "remotes",
        help="Verify that each repo has a remote alias that matches its directory name.",
    )
    remote_parser.add_argument(
        "--repos",
        nargs="*",
        help="Optional subset of repo names to inspect. Defaults to all tracked repos.",
    )
    remote_parser.add_argument(
        "--apply",
        action="store_true",
        help="Add the missing remote alias using the origin URL when needed.",
    )

    bootstrap_parser = subparsers.add_parser(
        "bootstrap", help="Bootstrap dependencies for a given repo (venv or pnpm)."
    )
    bootstrap_parser.add_argument(
        "repo", help="Target repo key from SUBREPO_CONTEXT (e.g., n00-frontiers)."
    )
    bootstrap_parser.add_argument(
        "--no-install",
        action="store_true",
        help="Skip dependency installation after venv/pnpm setup.",
    )

    return parser


def handle_radar(_: argparse.Namespace) -> None:
    run_script("project-lifecycle-radar.sh")


def handle_preflight(args: argparse.Namespace) -> None:
    cmd: List[str] = []
    if args.paths:
        cmd.extend(["--paths", *args.paths])
    if args.include_registry:
        cmd.append("--include-registry")
    run_script("project-preflight-batch.sh", *cmd)


def handle_control_panel(_: argparse.Namespace) -> None:
    run_script("project-control-panel.sh")


def handle_autofix_links(args: argparse.Namespace) -> None:
    cmd: List[str] = []
    for path in args.path_list:
        cmd.extend(["--path", path])
    if args.all:
        cmd.append("--all")
    if args.apply:
        cmd.append("--apply")
    run_script("project-autofix-links.sh", *cmd)


def handle_project_command(args: argparse.Namespace) -> None:
    script_name = PROJECT_COMMAND_SCRIPTS[args.command]
    run_script(script_name, "--path", args.path)


def handle_doctor(args: argparse.Namespace) -> None:
    flags: List[str] = ["--strict"] if args.strict else []
    run_workspace_script("workspace-gitdoctor-capability.sh", *flags)
    skeleton_flags: List[str] = []
    if args.strict:
        skeleton_flags.append("--apply")
    run_workspace_script("check-superrepo-skeleton.sh", *skeleton_flags)
    generate_repo_context_artifact()


def handle_upgrade_tools(args: argparse.Namespace) -> None:
    flags = ["--apply"] if args.apply else []
    run_script("get-latest-tool-versions.py", *flags)


def handle_status(_: argparse.Namespace) -> None:
    status_report()


def handle_manifest(args: argparse.Namespace) -> None:
    read_manifest(Path(args.path))


def handle_capabilities(args: argparse.Namespace) -> None:
    list_capabilities(args.id)


def handle_trunk_upgrade(args: argparse.Namespace) -> None:
    run_trunk_upgrade(args.repos)


def handle_trunk_alias(args: argparse.Namespace) -> None:
    run_trunk_upgrade(args.repos)


def handle_health_toolchain(_: argparse.Namespace) -> None:
    run(["pnpm", "run", "tools:check-toolchain"], cwd=WORKSPACE_ROOT)


def handle_health_runners(args: argparse.Namespace) -> None:
    env = os.environ.copy()
    env["REQUIRED_RUNNER_LABELS"] = args.required_labels
    if args.webhook:
        env["DISCORD_WEBHOOK"] = args.webhook
    run(["pnpm", "run", "tools:check-runners"], cwd=WORKSPACE_ROOT, env=env)


def handle_health_python_lock(_: argparse.Namespace) -> None:
    run(["pnpm", "run", "python:lock:check"], cwd=WORKSPACE_ROOT)


def handle_normalize_js(args: argparse.Namespace) -> None:
    cmd = [".dev/automation/scripts/normalize-workspace-pnpm.sh"]
    if args.allow_mismatch:
        cmd.append("--allow-mismatch")
    run(cmd, cwd=WORKSPACE_ROOT)


def handle_remotes(args: argparse.Namespace) -> None:
    targets = args.repos if args.repos else list(SUBREPO_MAP.keys())
    for name, path in iter_repos(targets):
        ensure_repo_remote(name, path, args.apply)


def handle_bootstrap(args: argparse.Namespace) -> None:
    name = args.repo
    meta = SUBREPO_CONTEXT.get(name)
    if not meta:
        raise SystemExit(
            f"Unknown repo '{name}'. Valid options: {', '.join(SUBREPO_CONTEXT.keys())}"
        )

    repo_root = meta.get("path")
    if not repo_root or not repo_root.exists():
        raise SystemExit(f"Repo path missing for '{name}': {repo_root}")

    language = meta.get("language")
    if language == "python":
        venv_path = meta.get("venv")
        if not venv_path:
            raise SystemExit(
                f"No venv configured for '{name}'. Update SUBREPO_CONTEXT."
            )
        python_bin = sys.executable
        run([python_bin, "-m", "venv", str(venv_path)], cwd=repo_root, check=True)
        pip_bin = venv_executable(venv_path, "pip")
        if not pip_bin.exists():
            raise SystemExit(f"Expected pip inside venv but not found at {pip_bin}")
        run(
            [str(pip_bin), "install", "-U", "pip", "setuptools", "wheel"], cwd=repo_root
        )
        reqs = repo_root / "requirements.txt"
        if reqs.exists() and not args.no_install:
            run([str(pip_bin), "install", "-r", str(reqs)], cwd=repo_root)
    else:
        # Default to pnpm bootstrap for non-Python repos.
        cmd = ["pnpm", "install", "--frozen-lockfile"]
        if args.no_install:
            cmd.append("--ignore-scripts")
        run(cmd, cwd=repo_root)

    generate_repo_context_artifact()
    print(f"[bootstrap] {name} ready at {repo_root}")


def generate_repo_context_artifact() -> Path:
    artifacts_dir = WORKSPACE_ROOT / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    ctx_path = artifacts_dir / "workspace-repo-context.json"
    serialisable = []
    for name, meta in SUBREPO_CONTEXT.items():
        serialisable.append(
            {
                "name": name,
                "path": str(meta.get("path")),
                "language": meta.get("language"),
                "packageManager": meta.get("pkg"),
                "venv": str(meta.get("venv")) if meta.get("venv") else None,
                "cli": meta.get("cli"),
                "toolingDir": str(meta.get("tooling")) if meta.get("tooling") else None,
                "scriptsDir": (
                    str(meta.get("scripts_dir")) if meta.get("scripts_dir") else None
                ),
            }
        )
    ctx_path.write_text(json.dumps(serialisable, indent=2) + "\n", encoding="utf-8")
    return ctx_path


COMMAND_HANDLERS = {
    "radar": handle_radar,
    "preflight": handle_preflight,
    "control-panel": handle_control_panel,
    "autofix-links": handle_autofix_links,
    "capture": handle_project_command,
    "sync-github": handle_project_command,
    "sync-erpnext": handle_project_command,
    "doctor": handle_doctor,
    "upgrade-tools": handle_upgrade_tools,
    "status": handle_status,
    "manifest": handle_manifest,
    "capabilities": handle_capabilities,
    "trunk-upgrade": handle_trunk_upgrade,
    "trunk": handle_trunk_alias,
    "health-toolchain": handle_health_toolchain,
    "health-runners": handle_health_runners,
    "health-python-lock": handle_health_python_lock,
    "normalize-js": handle_normalize_js,
    "remotes": handle_remotes,
    "bootstrap": handle_bootstrap,
    "repo-context": lambda _: generate_repo_context_artifact(),
    "docs-sync": handle_docs_sync,
    "docs-verify": handle_docs_verify,
    "docs-lint": handle_docs_lint,
}


def main(argv: Optional[List[str]] = None) -> int:
    # Best-effort OTLP tracing so automation runs show up in the shared collector.
    initialize_tracing("n00tropic-workspace-cli")
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = COMMAND_HANDLERS.get(args.command)
    if not handler:
        parser.print_help()
        return 1
    handler(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
