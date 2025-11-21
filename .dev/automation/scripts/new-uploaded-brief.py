#!/usr/bin/env python3
"""Scaffold a metadata-bearing brief from the uploaded-brief template."""

from __future__ import annotations

import argparse
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

from lib import project_metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True, help="Slug for the brief (used in id/path).")
    parser.add_argument("--title", required=True, help="Title for the brief.")
    parser.add_argument("--owner", required=True, help="Owner/team handle.")
    parser.add_argument(
        "--kind",
        choices=["idea", "project", "learn"],
        default="idea",
        help="Brief classification; determines defaults and destination path.",
    )
    parser.add_argument("--tags", nargs="*", default=[], help="Additional tags to apply.")
    parser.add_argument(
        "--review-days",
        type=int,
        default=30,
        help="Review window in days used to set review_date.",
    )
    parser.add_argument(
        "--path",
        type=Path,
        help="Optional explicit path for the brief. Defaults to derived location per kind.",
    )
    parser.add_argument(
        "--link",
        action="append",
        default=[],
        help="Optional link spec (type:path), e.g., adr:n00tropic-cerebrum/1. Cerebrum Docs/ADR/ADR-004-unified-project-management-system.md",
    )
    parser.add_argument(
        "--register",
        action="store_true",
        help="Automatically run project-ingest-markdown to register the brief after scaffolding.",
    )
    return parser.parse_args()


def default_path(kind: str, slug: str, workspace_root: Path) -> Path:
    if kind == "idea":
        return workspace_root / "n00-horizons" / "ideas" / slug / "README.md"
    if kind == "learn":
        return workspace_root / "n00-horizons" / "learning-log" / f"{slug}.md"
    # project (experiment-style brief)
    return workspace_root / "n00-horizons" / "docs" / "experiments" / f"{slug}.md"


def kind_defaults(kind: str) -> Dict[str, object]:
    if kind == "idea":
        return {
            "lifecycle_stage": "discover",
            "status": "proposed",
            "tags": ["governance/project-management", "knowledge/idea"],
            "id_prefix": "idea",
        }
    if kind == "learn":
        return {
            "lifecycle_stage": "discover",
            "status": "recorded",
            "tags": ["governance/project-management", "knowledge/learning-log"],
            "id_prefix": "learn",
        }
    return {
        "lifecycle_stage": "shape",
        "status": "in-definition",
        "tags": ["governance/project-management"],
        "id_prefix": "project",
    }


def main() -> int:
    args = parse_args()
    _, workspace_root, org_root = project_metadata.resolve_roots()
    meta_defaults = kind_defaults(args.kind)

    review_date = (
        datetime.now(timezone.utc) + timedelta(days=args.review_days)
        if args.review_days > 0
        else datetime.now(timezone.utc)
    )
    review_date_str = project_metadata.format_display_date(review_date)

    identifier = f"{meta_defaults['id_prefix']}-{args.slug}"
    target_path = args.path.resolve() if args.path else default_path(args.kind, identifier, workspace_root)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    links: List[Dict[str, str]] = []
    for link_spec in args.link:
        if ":" in link_spec:
            link_type, link_path = link_spec.split(":", 1)
        else:
            link_type, link_path = "doc", link_spec
        links.append({"type": link_type, "path": link_path})

    front_matter: Dict[str, object] = {
        "id": identifier,
        "title": args.title,
        "lifecycle_stage": meta_defaults["lifecycle_stage"],
        "status": meta_defaults["status"],
        "owner": args.owner,
        "sponsors": [],
        "source": "uploaded-brief",
        "review_date": review_date_str,
        "erpnext_project": "PM-TBD",
        "erpnext_task": "",
        "github_project": "https://github.com/orgs/n00tropic/projects/1",
        "tags": list(dict.fromkeys(meta_defaults["tags"] + args.tags)),
        "links": links,
    }

    body = f"""---
{project_metadata.yaml.safe_dump(front_matter, sort_keys=False).strip()}
---

# Brief — {args.title}

## Objective / Outcome

- What outcome are we aiming for? How will we know it succeeded?
- If this brief will become a job, be explicit about definition of done.

## Scope & Deliverables

- In-scope items (features, documents, datasets, integrations).
- Out-of-scope items to avoid scope creep.

## Dependencies & Integrations

- Systems/repos/services impacted.
- ERPNext/GitHub linkage needs (project codes, tasks, board lanes).

## Risks & Mitigations

- Top risks, mitigations, rollback/contingency.

## Acceptance & Evidence

- Tests/validations, telemetry artefacts, dashboards to update.

## Next Actions

- [ ] Run `.dev/automation/scripts/project-ingest-markdown.sh --path {str(target_path.relative_to(org_root))} --kind {args.kind} --owner {args.owner}` to register.
- [ ] When delivery-ready, run `.dev/automation/scripts/project-record-job.sh --link {meta_defaults['id_prefix']}:{str(target_path.relative_to(org_root))} --title \"{args.title}\" --owner {args.owner}` (or use `job-from-brief.sh --from {str(target_path.relative_to(org_root))}`).
- [ ] Run `project-preflight.sh --path <job>` before kicking off work; attach artefacts to learning log.
"""
    target_path.write_text(body, encoding="utf-8")
    print(str(target_path))

    if args.register:
        ingest_script = org_root / ".dev" / "automation" / "scripts" / "project-ingest-markdown.sh"
        if not ingest_script.exists():
            raise SystemExit(f"Ingest script not found at {ingest_script}")
        rel_path = str(target_path.relative_to(org_root))
        cmd = [
            str(ingest_script),
            "--path",
            rel_path,
            "--kind",
            args.kind,
            "--owner",
            args.owner,
        ]
        if args.tags:
            cmd.extend(["--tags", *args.tags])
        subprocess.run(cmd, check=True, cwd=org_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
