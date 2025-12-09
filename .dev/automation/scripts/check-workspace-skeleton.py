#!/usr/bin/env python3
"""Validate workspace repos against the skeleton definition."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

import yaml

DOC_ROLES = {"docs-ssot", "docs", "techdocs", "docs-only"}
CODE_REQUIRED_DEFAULTS = [
    "cli",
    "env",
    "scripts",
    "tests",
    "artifacts",
    "automation",
    "tooling",
]


def is_doc_repo(role: str | None) -> bool:
    if not role:
        return False
    lowered = role.lower()
    return any(key in lowered for key in DOC_ROLES) or "docs" in lowered


def normalize_required(required: List[str], role: str | None) -> List[str]:
    """Augment required paths for code repos with standard defaults."""
    if is_doc_repo(role):
        return required
    combined = set(required) | set(CODE_REQUIRED_DEFAULTS)
    return sorted(combined)


def discover_cli_targets(cli_cmd: str, repo_root: Path) -> List[str]:
    """Return referenced files within CLI command that should exist."""
    missing: List[str] = []
    if not cli_cmd:
        return ["<unset CLI command>"]
    for token in cli_cmd.split():
        if "/" not in token or token.startswith("-"):
            continue
        candidate = repo_root / token
        if not candidate.exists():
            missing.append(str(candidate))
    return missing


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


MANIFEST_PATH = (
    Path(__file__).resolve().parents[3] / "automation" / "workspace.manifest.json"
)


def load_skeleton(skeleton_path: Path) -> Dict[str, object]:
    if not skeleton_path.exists():
        raise SystemExit(f"Skeleton file missing: {skeleton_path}")
    return yaml.safe_load(skeleton_path.read_text(encoding="utf-8")) or {}


def load_manifest() -> Dict[str, object]:
    if not MANIFEST_PATH.exists():
        return {}
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # pragma: no cover - diagnostic
        print(f"[manifest] unable to read {MANIFEST_PATH}: {exc}", file=sys.stderr)
        return {}


def ensure_dir(path: Path, apply: bool, alternates: List[Path] | None = None) -> bool:
    alternates = alternates or []
    if path.exists() or any(alt.exists() for alt in alternates):
        return False
    if apply:
        path.mkdir(parents=True, exist_ok=True)
        gitkeep = path / ".gitkeep"
        gitkeep.touch(exist_ok=True)
    return True


def scaffold_stub(path: Path, apply: bool) -> List[str]:
    """Create minimal stub files for commonly-required dirs (docs, scripts)."""

    created: List[str] = []
    if not apply:
        return created

    if path.name == "docs":
        readme = path / "README.md"
        if not readme.exists():
            readme.write_text(
                "# Docs\n\nWorkspace docs placeholder.\n", encoding="utf-8"
            )
            created.append(str(readme))
        tags = path / "TAGS.md"
        if not tags.exists():
            tags.write_text("<!-- Tag propagation placeholder -->\n", encoding="utf-8")
            created.append(str(tags))

    if path.name == "scripts":
        runner = path / "README.md"
        if not runner.exists():
            runner.write_text(
                "# Scripts\n\nAdd automation entrypoints here; surfaced via n00t capabilities.\n",
                encoding="utf-8",
            )
            created.append(str(runner))
        hook = path / "install-hooks.sh"
        if not hook.exists():
            hook.write_text(
                '#!/usr/bin/env bash\ncd "$(dirname "$0")/.." && bash scripts/install-hooks.sh\n',
                encoding="utf-8",
            )
            hook.chmod(0o755)
            created.append(str(hook))

    return created


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create missing directories + stubs and backfill manifest entries.",
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Provision toolchain (pnpm+trunk) and refresh submodules/health after validation.",
    )
    args = parser.parse_args()

    org_root = Path(__file__).resolve().parents[3]

    # Prefer JSON manifest; fall back to YAML skeleton for required paths/branches.
    manifest_payload = load_manifest()
    manifest_repos = manifest_payload.get("repos") or []
    manifest_defaults = (manifest_payload.get("meta") or {}).get("defaults", {})

    skeleton_path = org_root / ".dev" / "automation" / "workspace-skeleton.yaml"
    skeleton_payload = load_skeleton(skeleton_path)
    skeleton_repos = skeleton_payload.get("repos") or {}

    repos_obj = {}
    # Merge: manifest provides identity/paths; skeleton adds required/branches if present.
    for entry in manifest_repos:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not name:
            continue
        repos_obj[name] = {
            "path": entry.get("path"),
            "required": (
                entry.get("required")
                if "required" in entry
                else manifest_defaults.get("required") or []
            ),
            "branches": (
                entry.get("branches")
                if "branches" in entry
                else manifest_defaults.get("branches") or []
            ),
            "role": entry.get("role"),
        }
        for key in ("cli", "language", "pkg", "venv", "tooling", "scripts_dir"):
            if key in entry:
                repos_obj[name][key] = entry.get(key)

    for name, spec in skeleton_repos.items():
        merged = repos_obj.setdefault(name, {})
        if "path" not in merged and spec.get("path"):
            merged["path"] = spec.get("path")
        merged["required"] = (
            spec.get("required")
            if "required" in spec
            else merged.get("required") or manifest_defaults.get("required") or []
        )
        merged["branches"] = (
            spec.get("branches")
            if "branches" in spec
            else merged.get("branches") or manifest_defaults.get("branches") or []
        )

    # detect repos present on disk or in gitmodules but missing from manifest
    present_gitmodules = {
        mod.get("name"): mod.get("path", mod.get("name"))
        for mod in parse_gitmodules(org_root / ".gitmodules")
    }
    present_git_roots = {
        p.name: p for p in org_root.iterdir() if (p / ".git").exists() and p.is_dir()
    }

    missing_manifest: List[str] = []
    generated_manifest_entries: List[dict] = []

    for mod_name in set(present_gitmodules.keys()) | set(present_git_roots.keys()):
        if mod_name not in repos_obj:
            missing_manifest.append(mod_name)
            if args.apply:
                repos_obj[mod_name] = {
                    "path": present_gitmodules.get(mod_name, mod_name),
                    "required": manifest_defaults.get("required", []),
                    "branches": manifest_defaults.get("branches", []),
                    "role": "unknown",
                }
                generated_manifest_entries.append(
                    repos_obj[mod_name] | {"name": mod_name}
                )

    summary: Dict[str, object] = {"status": "ok", "repos": []}
    missing_total = 0

    for name, spec in repos_obj.items():
        if not isinstance(spec, dict):
            continue
        rel_path = spec.get("path")
        role = spec.get("role")
        required = normalize_required(spec.get("required") or [], role)
        spec["required"] = required
        expected_branches = spec.get("branches") or []
        if not rel_path:
            continue
        repo_root = (org_root / str(rel_path)).resolve()
        repo_missing: List[str] = []
        created_stubs: List[str] = []
        cli_missing: List[str] = []
        env_missing: List[str] = []
        for req in required:
            req_path = repo_root / req
            alternates: List[Path] = []
            if req_path.name.lower() == "tests":
                alternates.append(repo_root / "Tests")
            if ensure_dir(req_path, args.apply, alternates=alternates):
                repo_missing.append(str(req_path))
            created_stubs.extend(scaffold_stub(req_path, args.apply))

        if not is_doc_repo(role):
            cli_cmd = spec.get("cli", "")
            cli_missing.extend(discover_cli_targets(cli_cmd, repo_root))
            env_example = repo_root / ".env.example"
            if not env_example.exists() and args.apply:
                template = org_root / ".env.example"
                if template.exists():
                    env_example.write_text(
                        template.read_text(encoding="utf-8"), encoding="utf-8"
                    )
                else:
                    env_example.write_text("# env placeholder\n", encoding="utf-8")
            if not env_example.exists():
                env_missing.append(str(env_example))

        branch_missing: List[str] = []
        if expected_branches:
            # Verify remote branches exist (origin required)
            try:
                out = subprocess.check_output(
                    ["git", "-C", str(repo_root), "ls-remote", "--heads", "origin"],
                    text=True,
                )
                remote_heads = {
                    line.split()[1].split("refs/heads/")[-1]
                    for line in out.splitlines()
                    if line.strip()
                }
                for br in expected_branches:
                    if br not in remote_heads:
                        branch_missing.append(br)
            except subprocess.CalledProcessError:
                branch_missing = expected_branches

        if repo_missing:
            missing_total += len(repo_missing)
            summary["status"] = "attention"
        if branch_missing:
            missing_total += len(branch_missing)
            summary["status"] = "attention"
        if cli_missing:
            missing_total += len(cli_missing)
            summary["status"] = "attention"
        if env_missing:
            missing_total += len(env_missing)
            summary["status"] = "attention"
        summary["repos"].append(
            {
                "name": name,
                "path": str(repo_root),
                "missing": repo_missing,
                "missing_branches": branch_missing,
                "role": spec.get("role"),
                "created_stubs": created_stubs,
                "missing_cli_targets": cli_missing,
                "missing_env_examples": env_missing,
            }
        )

    if missing_manifest:
        summary["status"] = "attention"
        summary["missing_manifest_entries"] = sorted(missing_manifest)
        if args.apply and generated_manifest_entries:
            summary["generated_manifest_entries"] = generated_manifest_entries
            try:
                payload = load_manifest() or {}
                repos = payload.get("repos") or []
                repos.extend(generated_manifest_entries)
                payload["repos"] = repos
                MANIFEST_PATH.write_text(
                    json.dumps(payload, indent=2, sort_keys=False) + "\n",
                    encoding="utf-8",
                )
            except Exception as exc:  # pragma: no cover - defensive write
                summary.setdefault("errors", []).append(
                    f"failed to write manifest: {exc}"
                )

    print(json.dumps(summary, indent=2))

    if args.bootstrap:
        # Provision pnpm + trunk, sync submodules, run trunk check
        subprocess.run([str(org_root / "scripts" / "setup-pnpm.sh")], check=False)
        subprocess.run(
            [str(org_root / "scripts" / "trunk-upgrade-workspace.sh"), "--check"],
            check=False,
        )
        subprocess.run(
            [
                str(
                    org_root / ".dev" / "automation" / "scripts" / "workspace-health.py"
                ),
                "--sync-submodules",
                "--publish-artifact",
            ],
            check=False,
        )

    return 1 if missing_total and not args.apply else 0


if __name__ == "__main__":
    raise SystemExit(main())
