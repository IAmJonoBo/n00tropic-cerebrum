#!/usr/bin/env python3
"""Fetch the latest published versions for runtimes and Trunk-managed linters."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Callable, Dict, Optional, Sequence, Tuple

HEADERS = {"User-Agent": "n00tropic-cerebrum-version-check/1.0"}


class FetchError(RuntimeError):
    """Raised when a version lookup fails."""


def _http_get(url: str) -> bytes:
    request = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return response.read()
    except urllib.error.URLError as exc:  # pragma: no cover - network failures
        raise FetchError(f"Failed to fetch {url}: {exc}") from exc


def _strip_v(tag: str) -> str:
    return tag[1:] if tag.startswith("v") else tag


def fetch_github_release(repo: str) -> str:
    payload = json.loads(
        _http_get(f"https://api.github.com/repos/{repo}/releases/latest").decode(
            "utf-8"
        )
    )
    tag = payload.get("tag_name")
    if not isinstance(tag, str):
        raise FetchError(f"Release tag missing for {repo}")
    return _strip_v(tag)


def fetch_npm(package: str) -> str:
    payload = json.loads(
        _http_get(f"https://registry.npmjs.org/{package}/latest").decode("utf-8")
    )
    version = payload.get("version")
    if not isinstance(version, str):
        raise FetchError(f"npm version missing for {package}")
    return version


def fetch_pypi(package: str) -> str:
    payload = json.loads(
        _http_get(f"https://pypi.org/pypi/{package}/json").decode("utf-8")
    )
    info = payload.get("info") or {}
    version = info.get("version")
    if not isinstance(version, str):
        raise FetchError(f"PyPI version missing for {package}")
    return version


def fetch_node_lts() -> str:
    payload = json.loads(
        _http_get("https://nodejs.org/dist/index.json").decode("utf-8")
    )
    for entry in payload:
        lts = entry.get("lts")
        if lts and isinstance(lts, str):
            return entry["version"].lstrip("v")
    raise FetchError("No LTS Node.js release found")


def fetch_go() -> str:
    payload = json.loads(
        _http_get("https://go.dev/dl/?mode=json&include=all").decode("utf-8")
    )
    if not payload:
        raise FetchError("Empty Go release feed")
    latest = payload[0]
    version = latest.get("version")
    if not isinstance(version, str):
        raise FetchError("Go version missing from feed")
    return version.lstrip("go")


def _cycle_key(cycle: str) -> Tuple[int, ...]:
    parts: Sequence[str] = cycle.split(".")
    numeric = []
    for part in parts:
        try:
            numeric.append(int(part))
        except ValueError:
            break
    return tuple(numeric)


def fetch_python() -> str:
    payload = json.loads(
        _http_get("https://endoflife.date/api/python.json").decode("utf-8")
    )
    today = date.today()
    active = []
    for entry in payload:
        eol = entry.get("eol")
        if not eol:
            active.append(entry)
            continue
        try:
            eol_date = date.fromisoformat(eol)
        except ValueError:
            continue
        if eol_date >= today:
            active.append(entry)
    if not active:
        active = payload
    active.sort(key=lambda item: _cycle_key(item.get("cycle", "")), reverse=True)
    latest = active[0]
    latest_release = latest.get("latest")
    if not isinstance(latest_release, str):
        raise FetchError("Python latest release missing")
    return latest_release


def fetch_trunk_plugins_ref() -> str:
    release = fetch_github_release("trunk-io/plugins")
    return f"v{release}"


FetchFn = Callable[[], str]


@dataclass(frozen=True)
class Artifact:
    name: str
    fetcher: FetchFn


ARTIFACTS: Dict[str, Artifact] = {
    "node": Artifact("node", fetch_node_lts),
    "pnpm": Artifact("pnpm", lambda: fetch_npm("pnpm")),
    "python": Artifact("python", fetch_python),
    "go": Artifact("go", fetch_go),
    "trunk-plugins": Artifact("trunk-plugins", fetch_trunk_plugins_ref),
    "hadolint": Artifact("hadolint", lambda: fetch_github_release("hadolint/hadolint")),
    "svgo": Artifact("svgo", lambda: fetch_npm("svgo")),
    "golangci-lint2": Artifact(
        "golangci-lint2", lambda: fetch_github_release("golangci/golangci-lint")
    ),
    "actionlint": Artifact(
        "actionlint", lambda: fetch_github_release("rhysd/actionlint")
    ),
    "bandit": Artifact("bandit", lambda: fetch_pypi("bandit")),
    "checkov": Artifact("checkov", lambda: fetch_pypi("checkov")),
    "markdownlint-cli2": Artifact(
        "markdownlint-cli2", lambda: fetch_npm("markdownlint-cli2")
    ),
    "eslint": Artifact("eslint", lambda: fetch_npm("eslint")),
    "osv-scanner": Artifact(
        "osv-scanner", lambda: fetch_github_release("google/osv-scanner")
    ),
    "prettier": Artifact("prettier", lambda: fetch_npm("prettier")),
    "renovate": Artifact("renovate", lambda: fetch_npm("renovate")),
    "ruff": Artifact("ruff", lambda: fetch_pypi("ruff")),
    "shellcheck": Artifact(
        "shellcheck", lambda: fetch_github_release("koalaman/shellcheck")
    ),
    "shfmt": Artifact("shfmt", lambda: fetch_github_release("mvdan/sh")),
    "taplo": Artifact("taplo", lambda: fetch_github_release("tamasfe/taplo")),
    "trufflehog": Artifact(
        "trufflehog", lambda: fetch_github_release("trufflesecurity/trufflehog")
    ),
    "yamllint": Artifact("yamllint", lambda: fetch_pypi("yamllint")),
}


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON with the collected versions."
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress human-readable output."
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    results: Dict[str, str] = {}
    failed = False
    for key, artifact in ARTIFACTS.items():
        try:
            version = artifact.fetcher()
        except FetchError as exc:
            print(f"[latest] {artifact.name}: {exc}", file=sys.stderr)
            failed = True
            continue
        results[key] = version
        if not args.quiet:
            print(f"{artifact.name}: {version}")

    if args.json:
        output: Dict[str, Optional[str]] = {key: results.get(key) for key in ARTIFACTS}
        print(json.dumps(output, indent=2))

    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
