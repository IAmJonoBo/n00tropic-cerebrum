#!/usr/bin/env python3
"""Generate aggregated Renovate/Dependency dashboard data for the workspace."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[3]
AUTOMATION_DIR = ROOT / ".dev" / "automation"
DEFAULT_OUTPUT = (
    AUTOMATION_DIR / "artifacts" / "dependencies" / "renovate-dashboard.json"
)
DEFAULT_REPOS = [
    "n00-frontiers",
    "n00-cortex",
    "n00t",
    "n00tropic",
    "n00plicate",
]
RENOVATE_BOT = "renovate[bot]"
SEVERITY_ORDER = {"critical": 0, "warning": 1, "informational": 2}
PACKAGE_PATTERN = re.compile(
    r"update (?:dependency )?([\w@\-/\.]+)(?: to v?([^\s]+))?",
    re.IGNORECASE,
)
SECRETS_FILE = ROOT / ".secrets" / "renovate" / "config.js"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=(
            "Destination JSON file (default: .dev/automation/artifacts/dependencies/renovate-dashboard.json)"
        ),
    )
    parser.add_argument(
        "--repo",
        action="append",
        dest="repos",
        help="Override repository directories (relative to workspace root). Repeatable.",
    )
    parser.add_argument(
        "--token",
        help="GitHub token (defaults to GITHUB_TOKEN or GH_TOKEN environment variables)",
    )
    parser.add_argument(
        "--owner",
        help="Fallback GitHub owner/organisation when it cannot be inferred from git remotes.",
    )
    return parser.parse_args()


def resolve_token(explicit: Optional[str]) -> Optional[str]:
    if explicit:
        return explicit
    for env_key in ("GITHUB_TOKEN", "GH_TOKEN", "RENOVATE_TOKEN"):
        value = os.getenv(env_key)
        if value:
            return value
    if SECRETS_FILE.exists():
        try:
            contents = SECRETS_FILE.read_text(encoding="utf-8")
        except OSError:
            return None
        match = re.search(r'RENOVATE_TOKEN\s*=\s*"([^"]+)"', contents)
        if match:
            return match.group(1)
    return None


def run_git(args: Sequence[str], cwd: Path) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout.strip() or None


def parse_remote(url: str, fallback_owner: Optional[str]) -> Optional[Tuple[str, str]]:
    if url.endswith(".git"):
        url = url[:-4]
    if url.startswith("git@"):
        # git@github.com:owner/repo
        try:
            _, path = url.split(":", 1)
            owner, repo = path.split("/", 1)
        except ValueError:
            return None
        return owner, repo
    if url.startswith("https://") or url.startswith("http://"):
        parts = url.split("//", 1)[-1].split("/", 2)
        if len(parts) >= 3:
            owner, repo = parts[1], parts[2]
            return owner, repo
    if fallback_owner and "/" not in url:
        return fallback_owner, url
    if "/" in url:
        owner, repo = url.split("/", 1)
        return owner, repo
    return None


def detect_repositories(
    repos: Optional[Sequence[str]], fallback_owner: Optional[str]
) -> List[Tuple[str, str, str]]:
    candidates = list(repos) if repos else DEFAULT_REPOS
    detected: List[Tuple[str, str, str]] = []
    for repo_dir in candidates:
        path = ROOT / repo_dir
        if not (path.exists() and (path / ".git").exists()):
            continue
        remote = run_git(["config", "--get", "remote.origin.url"], path)
        parsed = parse_remote(remote, fallback_owner) if remote else None
        if parsed is None:
            continue
        owner, repo = parsed
        detected.append((repo_dir, owner, repo))
    return detected


def github_get(url: str, token: Optional[str]) -> Tuple[List[Dict], Dict[str, str]]:
    collected: List[Dict] = []
    headers: Dict[str, str] = {}
    next_url: Optional[str] = url
    while next_url:
        request = Request(next_url)
        request.add_header("Accept", "application/vnd.github+json")
        request.add_header("X-GitHub-Api-Version", "2022-11-28")
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        try:
            with urlopen(request) as response:
                headers = {key: value for key, value in response.getheaders()}
                payload = json.loads(response.read().decode("utf-8"))
                if isinstance(payload, list):
                    collected.extend(payload)
                else:
                    # unexpected payload shape
                    break
                next_url = parse_next_link(headers.get("Link"))
        except HTTPError as exc:
            raise RuntimeError(
                f"GitHub API error ({exc.code}) at {next_url}: {exc.reason}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"Failed to reach GitHub API at {next_url}: {exc.reason}"
            ) from exc
    return collected, headers


def parse_next_link(link_header: Optional[str]) -> Optional[str]:
    if not link_header:
        return None
    for segment in link_header.split(","):
        part = segment.strip()
        if part.endswith('rel="next"'):
            url_part = part.split(";", 1)[0].strip()
            if url_part.startswith("<") and url_part.endswith(">"):
                return url_part[1:-1]
    return None


def extract_dependency(pr_title: str) -> Optional[str]:
    match = PACKAGE_PATTERN.search(pr_title)
    if not match:
        return None
    name = match.group(1)
    version = match.group(2)
    if version:
        return f"{name}@{version}"
    return name


def classify_severity(pr: Dict) -> str:
    labels = {label.get("name", "").lower() for label in pr.get("labels", [])}
    title_lower = pr.get("title", "").lower()
    if "security" in labels or "security" in title_lower or "cve" in title_lower:
        return "critical"
    if "major" in title_lower:
        return "warning"
    if "minor" in title_lower or "patch" in title_lower or "dependencies" in labels:
        return "informational"
    return "warning"


def summarize_pr(pr: Dict) -> Dict[str, object]:
    dependency = extract_dependency(pr.get("title", ""))
    severity = classify_severity(pr)
    return {
        "number": pr.get("number"),
        "title": pr.get("title"),
        "url": pr.get("html_url"),
        "updated": pr.get("updated_at"),
        "labels": [label.get("name") for label in pr.get("labels", [])],
        "severity": severity,
        "dependency": dependency,
    }


def severity_sort_key(entry: Dict[str, object]) -> Tuple[int, str]:
    severity = entry.get("severity", "informational")
    order = SEVERITY_ORDER.get(str(severity), len(SEVERITY_ORDER))
    updated = str(entry.get("updated", ""))
    return order, updated


def generate_dashboard(
    detected: Sequence[Tuple[str, str, str]],
    token: Optional[str],
) -> Dict[str, object]:
    total = 0
    repositories: List[Dict[str, object]] = []
    aggregated_prs: List[Dict[str, object]] = []
    errors: List[str] = []

    for repo_dir, owner, repo_name in detected:
        api_url = (
            f"https://api.github.com/repos/{owner}/{repo_name}/pulls?"
            + urlencode({"state": "open", "per_page": 100})
        )
        try:
            pulls, headers = github_get(api_url, token)
        except RuntimeError as exc:
            errors.append(f"{owner}/{repo_name}: {exc}")
            repositories.append(
                {
                    "name": repo_name,
                    "owner": owner,
                    "path": repo_dir,
                    "pendingPRs": 0,
                    "status": "error",
                    "message": str(exc),
                }
            )
            continue

        renovate_prs = []
        for pr in pulls:
            labels = {label.get("name", "").lower() for label in pr.get("labels", [])}
            login = (pr.get("user") or {}).get("login", "").lower()
            head_ref = ((pr.get("head") or {}).get("ref") or "").lower()
            if (
                login == RENOVATE_BOT
                or "renovate" in labels
                or head_ref.startswith("renovate/")
            ):
                renovate_prs.append(pr)

        summarized = [summarize_pr(pr) for pr in renovate_prs]
        aggregated_prs.extend(summarized)
        total += len(summarized)
        repositories.append(
            {
                "name": repo_name,
                "owner": owner,
                "path": repo_dir,
                "pendingPRs": len(summarized),
                "status": "ok",
                "rateLimitRemaining": headers.get("X-RateLimit-Remaining"),
                "prs": summarized,
            }
        )

    aggregated_prs.sort(key=severity_sort_key)
    top_risks = [
        {
            "name": entry.get("dependency") or entry.get("title"),
            "severity": entry.get("severity", "informational"),
            "summary": entry.get("title"),
            "link": entry.get("url"),
        }
        for entry in aggregated_prs[:10]
    ]

    status = "ok"
    if errors and total:
        status = "partial"
    elif errors and not total:
        status = "error"

    payload: Dict[str, object] = {
        "generated": dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "status": status,
        "pendingPRs": total,
        "repositories": repositories,
        "topRisks": top_risks,
    }
    if errors:
        payload["errors"] = errors
    return payload


def main() -> int:
    args = parse_args()
    token = resolve_token(args.token)
    detected = detect_repositories(args.repos, args.owner)

    if not detected:
        data = {
            "generated": dt.datetime.now(dt.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "status": "error",
            "pendingPRs": 0,
            "repositories": [],
            "topRisks": [],
            "errors": ["No repositories detected for Renovate dashboard generation."],
        }
    else:
        data = generate_dashboard(detected, token)

    output_path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    summary = {
        "status": data.get("status", "ok"),
        "path": str(output_path),
        "pendingPRs": data.get("pendingPRs", 0),
    }
    print(f"[renovate-dashboard] Wrote dashboard → {output_path}", file=sys.stderr)
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
