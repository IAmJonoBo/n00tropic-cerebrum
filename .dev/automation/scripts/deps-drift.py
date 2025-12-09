#!/usr/bin/env python3
"""Dependency drift + deprecation helper for the workspace.

AGENT_HOOK: dependency-management

Finds version mismatches across package ecosystems (Node/pnpm via package.json,
Python requirements*.txt) and highlights known deprecated packages with
suggested replacements. Designed to be dependency-free (stdlib only) so agents
can run it in constrained environments.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = ROOT / "artifacts" / "deps-drift" / "latest.json"
DEFAULT_TABLE = ROOT / "artifacts" / "deps-drift" / "latest.md"
DEFAULT_PLAN = ROOT / "artifacts" / "deps-drift" / "plan.json"
MANIFEST = ROOT / "automation" / "workspace.manifest.json"

# Curated deprecation/replacement hints (extend as needed)
DEPRECATION_MAP = {
    "left-pad": "Use native String.padStart / padEnd",
    "request": "Switch to node-fetch, undici, or axios",
    "uuid": "Use uuid@^9 with ESM import or crypto.randomUUID()",
    "ts-node": "Prefer tsx or node --loader ts-node/esm (latest)",
    "tslint": "Migrate to ESLint + typescript-eslint",
    "node-sass": "Replace with sass (dart-sass)",
    "@angular/http": "Migrate to @angular/common/http",
    "@babel/polyfill": "Use core-js + regenerator-runtime per Babel docs",
    "moment": "Consider luxon, date-fns, or Intl APIs",
    # n00 org specific
    "npm-run-all": "Switch to npm-run-all2 or native npm scripts",
    "rimraf": "Use rm -rf (Unix) or del-cli / clean scripts",
    "gulp": "Replace with npm scripts or lightweight task runners",
    "grunt": "Replace with npm scripts or lightweight task runners",
    "babel-eslint": "Use @babel/eslint-parser",
    "ts-jest": "Prefer tsx + vitest/jest with ESM support",
}


def load_manifest() -> List[Tuple[str, Path]]:
    if not MANIFEST.exists():
        raise SystemExit(f"Manifest not found at {MANIFEST}")
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    repos = []
    for repo in data.get("repos", []):
        name = repo.get("name")
        path = repo.get("path")
        if name and path:
            repos.append((name, ROOT / path))
    return repos


def _normalize_npm_spec(spec: str) -> str:
    spec = spec.strip()
    # Ignore workspace protocol specs which are intentionally floating
    if spec.startswith("workspace:"):
        return spec
    # Take first comparator in simple ranges (split on space or ||)
    spec = spec.split("||", 1)[0].strip()
    spec = spec.split(" ", 1)[0].strip()
    # Remove leading range operators commonly used by npm/pnpm
    spec = spec.lstrip("^~><= ")
    return spec


def parse_package_json(pkg: Path) -> Dict[str, str]:
    payload = json.loads(pkg.read_text(encoding="utf-8"))
    deps: Dict[str, str] = {}
    for field in (
        "dependencies",
        "devDependencies",
        "optionalDependencies",
        "peerDependencies",
    ):
        section = payload.get(field) or {}
        for name, spec in section.items():
            deps[name] = _normalize_npm_spec(str(spec))
    return deps


REQ_RE = re.compile(r"^([A-Za-z0-9_.\-]+)([<>=!~]{1,2})([A-Za-z0-9_.+\-]+)")


def parse_requirements(req: Path) -> Dict[str, str]:
    deps: Dict[str, str] = {}
    for line in req.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-") or ";" in line:
            continue  # skip options and environment markers for simplicity
        m = REQ_RE.match(line)
        if m:
            pkg, _op, ver = m.groups()
            deps[pkg] = ver
    return deps


def version_core(spec: str) -> str:
    match = re.search(r"([0-9]+(?:\.[0-9]+)*)", spec)
    return match.group(1) if match else spec


def version_key(spec: str) -> Tuple[int, ...]:
    core = version_core(spec)
    parts = []
    for part in core.split("."):
        if part == "":
            continue
        try:
            parts.append(int(part))
        except ValueError:
            break
    return tuple(parts)


def aggregate(ignore: Iterable[str]) -> Dict[str, Dict[str, Dict[str, str]]]:
    """Return ecosystem -> package -> {repo: version} mapping."""
    ignores = set(ignore)
    repos = load_manifest()
    npm: Dict[str, Dict[str, str]] = defaultdict(dict)
    py: Dict[str, Dict[str, str]] = defaultdict(dict)

    for name, path in repos:
        pkg_json = path / "package.json"
        if pkg_json.exists():
            for dep, spec in parse_package_json(pkg_json).items():
                if dep in ignores or spec.startswith("workspace:"):
                    continue
                npm[dep][name] = spec

        for req in path.glob("requirements*.txt"):
            for dep, spec in parse_requirements(req).items():
                if dep in ignores:
                    continue
                py[dep][name] = spec

    return {"npm": npm, "python": py}


def mismatches(ecosystem: str, data: Dict[str, Dict[str, str]]) -> List[dict]:
    findings = []
    for pkg, versions in sorted(data.items()):
        # normalise caret/tilde ranges that resolved to same core version
        unique = {version_core(v) for v in versions.values()}
        if len(unique) <= 1:
            continue
        best = max(unique, key=version_key)
        findings.append(
            {
                "package": pkg,
                "ecosystem": ecosystem,
                "versions": versions,
                "recommended": best,
            }
        )
    return findings


def deprecated_hits(ecosystem: str, data: Dict[str, Dict[str, str]]) -> List[dict]:
    hits = []
    for pkg, versions in sorted(data.items()):
        if pkg not in DEPRECATION_MAP:
            continue
        hits.append(
            {
                "package": pkg,
                "ecosystem": ecosystem,
                "repos": sorted(versions.keys()),
                "replacement": DEPRECATION_MAP[pkg],
            }
        )
    return hits


def format_table(mismatches: List[dict], deprecated: List[dict]) -> str:
    lines: List[str] = []
    if mismatches:
        lines.append("## Version mismatches")
        lines.append("pkg | ecosystem | recommended | details")
        lines.append("--- | --- | --- | ---")
        for item in mismatches:
            details = ", ".join(
                f"{repo}:{ver}" for repo, ver in sorted(item["versions"].items())
            )
            lines.append(
                f"{item['package']} | {item['ecosystem']} | {item['recommended']} | {details}"
            )
        lines.append("")
    if deprecated:
        lines.append("## Deprecated/replace")
        lines.append("pkg | ecosystem | replacement | repos")
        lines.append("--- | --- | --- | ---")
        for item in deprecated:
            lines.append(
                f"{item['package']} | {item['ecosystem']} | {item['replacement']} | {', '.join(item['repos'])}"
            )
    return "\n".join(lines)


def build_plan(mismatches: List[dict]) -> dict:
    plan = {}
    for item in mismatches:
        pkg = item["package"]
        plan[pkg] = {
            "ecosystem": item["ecosystem"],
            "recommended": item["recommended"],
            "repos": item["versions"],
        }
    return plan


def main(argv: Iterable[str]) -> int:
    parser = argparse.ArgumentParser(description="Dependency drift detector")
    parser.add_argument(
        "--format",
        choices=["json", "table", "both"],
        default="both",
        help="Output format",
    )
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        help="Package(s) to ignore (repeatable)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Write JSON summary to this path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--table-output",
        type=Path,
        default=DEFAULT_TABLE,
        help=f"Write table summary to this path (default: {DEFAULT_TABLE})",
    )
    parser.add_argument(
        "--plan-output",
        type=Path,
        default=DEFAULT_PLAN,
        help=f"Write bump plan JSON to this path (default: {DEFAULT_PLAN})",
    )
    parser.add_argument(
        "--fail-on",
        choices=["any", "major"],
        help="Exit non-zero when mismatches exist (any or major-only)",
    )

    args = parser.parse_args(list(argv))

    agg = aggregate(args.ignore)
    mismatch_list = mismatches("npm", agg["npm"]) + mismatches("python", agg["python"])
    deprecated_list = deprecated_hits("npm", agg["npm"]) + deprecated_hits(
        "python", agg["python"]
    )
    plan = build_plan(mismatch_list)

    for path in [args.output, args.table_output, args.plan_output]:
        path.parent.mkdir(parents=True, exist_ok=True)

    args.output.write_text(
        json.dumps(
            {"mismatches": mismatch_list, "deprecated": deprecated_list}, indent=2
        ),
        encoding="utf-8",
    )

    table = format_table(mismatch_list, deprecated_list)
    args.table_output.write_text(
        table if table else "No mismatches or deprecated packages found.\n",
        encoding="utf-8",
    )

    args.plan_output.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    exit_code = 0
    if args.fail_on:
        if args.fail_on == "any" and mismatch_list:
            exit_code = 1
        elif args.fail_on == "major":
            majors = [
                m
                for m in mismatch_list
                if any(v.startswith("0") is False for v in m["versions"].values())
            ]
            if majors:
                exit_code = 1

    if args.format in ("json", "both"):
        print(
            json.dumps(
                {"mismatches": mismatch_list, "deprecated": deprecated_list}, indent=2
            )
        )
        if args.format == "json":
            print(
                f"[deps-drift] status={'ok' if exit_code==0 else 'fail'} output={args.output}"
            )
            return exit_code

    print(table if table else "No mismatches or deprecated packages found.")
    print(
        f"[deps-drift] status={'ok' if exit_code==0 else 'fail'} output={args.output}"
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
