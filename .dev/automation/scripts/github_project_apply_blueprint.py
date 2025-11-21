#!/usr/bin/env python3
"""Apply a GitHub Project configuration blueprint using the GitHub CLI GraphQL API."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_SCOPES = {"project", "read:project"}


class CLIError(RuntimeError):
    """Raised when a CLI invocation fails."""


@dataclass
class ProjectRef:
    project_id: str
    project_number: int
    url: str
    owner_type: str
    owner_login: str


@dataclass
class FieldInfo:
    typename: str
    field_id: str
    name: str
    data: Dict[str, Any]


def run_command(command: List[str], *, capture_output: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        command,
        check=False,
        capture_output=capture_output,
        text=True,
    )
    return result


def ensure_gh_available() -> None:
    result = run_command(["gh", "--version"])
    if result.returncode != 0:
        raise CLIError("GitHub CLI (gh) is not available on PATH")


def ensure_scopes(required: Iterable[str]) -> None:
    result = run_command(["gh", "auth", "status"])
    if result.returncode != 0:
        raise CLIError(
            "GitHub CLI is not authenticated. Run `gh auth login` before applying a blueprint."
        )

    scopes_line = ""
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("token scopes:"):
            scopes_line = stripped
            break

    scopes: set[str] = set()
    if scopes_line:
        _, _, scope_values = scopes_line.partition(":")
        for scope in scope_values.replace("'", "").split(","):
            scope = scope.strip()
            if scope:
                scopes.add(scope)

    missing = [scope for scope in required if scope not in scopes]
    if missing:
        raise CLIError(
            "Authentication token is missing required scopes ({}).\n"
            "Run `gh auth refresh -s {}` and retry.".format(
                ", ".join(missing), ",".join(required)
            )
        )


def load_blueprint(path: str) -> Dict[str, Any]:
    blueprint_path = Path(path)
    if not blueprint_path.is_absolute():
        blueprint_path = (REPO_ROOT / path).resolve()
    if not blueprint_path.exists():
        raise CLIError(f"Blueprint file not found: {path}")

    raw = blueprint_path.read_text(encoding="utf-8")
    # Strip cookiecutter placeholders so the document parses as JSON.
    rendered = re.sub(r"\{\{.*?\}\}", "", raw)

    try:
        data = json.loads(rendered)
    except json.JSONDecodeError as exc:
        raise CLIError(
            f"Failed to parse blueprint JSON (after removing cookiecutter placeholders): {exc}"
        ) from exc
    return data


def graphql(query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as query_file:
        query_file.write(query)
        query_path = query_file.name

    variables_path: Optional[str] = None
    try:
        command = [
            "gh",
            "api",
            "graphql",
            "-H",
            "GraphQL-Features: projects_next_graphql",
            "-f",
            f"query=@{query_path}",
        ]
        if variables is not None:
            with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as var_file:
                json.dump(variables, var_file)
                var_file.flush()
                variables_path = var_file.name
            command.extend(["-f", f"variables=@{variables_path}"])

        result = run_command(command)
        if result.returncode != 0:
            raise CLIError(result.stderr.strip() or result.stdout.strip())

        payload = json.loads(result.stdout)
        if "errors" in payload and payload["errors"]:
            messages = ", ".join(error.get("message", "Unknown GraphQL error") for error in payload["errors"])
            raise CLIError(messages)
        return payload.get("data", {})
    finally:
        try:
            os.unlink(query_path)
        except FileNotFoundError:
            pass
        if variables_path:
            try:
                os.unlink(variables_path)
            except FileNotFoundError:
                pass


def resolve_owner(owner: str) -> Tuple[str, str]:
    query = """
    query($login: String!) {
      user(login: $login) { id login }
      organization(login: $login) { id login }
    }
    """
    data = graphql(query, {"login": owner})
    if data.get("user"):
        return ("USER", data["user"]["id"])
    if data.get("organization"):
        return ("ORGANIZATION", data["organization"]["id"])
    raise CLIError(f"Owner '{owner}' not found (neither user nor organization)")


def list_projects(owner: str) -> List[Dict[str, Any]]:
    query = """
    query($login: String!) {
      user(login: $login) {
        projectsV2(first: 100) {
          nodes { id number title url }
        }
      }
      organization(login: $login) {
        projectsV2(first: 100) {
          nodes { id number title url }
        }
      }
    }
    """
    data = graphql(query, {"login": owner})
    container = data.get("user") or data.get("organization")
    nodes = container.get("projectsV2", {}).get("nodes", []) if container else []
    return nodes


def ensure_project(owner: str, title: str) -> ProjectRef:
    owner_type, owner_id = resolve_owner(owner)
    existing = list_projects(owner)
    for project in existing:
        if project.get("title") == title:
            return ProjectRef(
                project_id=project["id"],
                project_number=int(project["number"]),
                url=project["url"],
                owner_type=owner_type,
                owner_login=owner,
            )

    mutation = """
    mutation($ownerId: ID!, $title: String!) {
      createProjectV2(input: {ownerId: $ownerId, title: $title}) {
        projectV2 { id number url }
      }
    }
    """
    data = graphql(mutation, {"ownerId": owner_id, "title": title})
    project = data.get("createProjectV2", {}).get("projectV2")
    if not project:
        raise CLIError("Failed to create project (response missing project data)")
    return ProjectRef(
        project_id=project["id"],
        project_number=int(project["number"]),
        url=project["url"],
        owner_type=owner_type,
        owner_login=owner,
    )


def update_description(project_id: str, description: Optional[str]) -> None:
    if not description:
        return
    mutation = """
    mutation($projectId: ID!, $description: String) {
      updateProjectV2(input: {projectId: $projectId, description: $description}) {
        projectV2 { id }
      }
    }
    """
    graphql(mutation, {"projectId": project_id, "description": description})


def fetch_fields(project_id: str) -> Dict[str, FieldInfo]:
    query = """
    query($projectId: ID!) {
      projectV2(id: $projectId) {
        fields(first: 100) {
          nodes {
            __typename
            ... on ProjectV2FieldCommon {
              id
              name
              dataType
            }
            ... on ProjectV2SingleSelectField {
              id
              name
              options { id name }
            }
            ... on ProjectV2IterationField {
              id
              name
              configuration { duration startDay }
            }
          }
        }
      }
    }
    """
    data = graphql(query, {"projectId": project_id})
    nodes = (
        data.get("projectV2", {})
        .get("fields", {})
        .get("nodes", [])
    )
    fields: Dict[str, FieldInfo] = {}
    for node in nodes:
        typename = node.get("__typename", "")
        field_id = node.get("id")
        name = node.get("name")
        if not field_id or not name:
            continue
        payload = dict(node)
        fields[name] = FieldInfo(
            typename=typename,
            field_id=field_id,
            name=name,
            data=payload,
        )
    return fields


def normalise_status_options(columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    options: List[Dict[str, Any]] = []
    for column in columns:
        name = column.get("name")
        if not name:
            continue
        option: Dict[str, Any] = {"name": name}
        if column.get("description"):
            option["description"] = column["description"]
        if column.get("color"):
            option["color"] = column["color"].upper()
        options.append(option)
    return options


def update_status_field(project_id: str, fields: Dict[str, FieldInfo], columns: List[Dict[str, Any]]) -> None:
    if not columns:
        return
    status_field = fields.get("Status")
    if not status_field or status_field.typename != "ProjectV2SingleSelectField":
        raise CLIError("Status field not found or unexpected type; cannot configure columns")

    existing_options = {
        option.get("name"): option.get("id")
        for option in status_field.data.get("options", [])
        if option.get("name") and option.get("id")
    }

    desired = normalise_status_options(columns)
    payload: List[Dict[str, Any]] = []
    for option in desired:
        name = option["name"]
        entry = dict(option)
        if name in existing_options:
            entry["id"] = existing_options[name]
        payload.append(entry)

    mutation = """
    mutation($projectId: ID!, $fieldId: ID!, $options: [ProjectV2SingleSelectFieldOptionInput!]!) {
      updateProjectV2Field(
        input: {
          projectId: $projectId,
          fieldId: $fieldId,
          singleSelectOptions: $options
        }
      ) {
        projectV2Field { id }
      }
    }
    """
    graphql(
        mutation,
        {
            "projectId": project_id,
            "fieldId": status_field.field_id,
            "options": payload,
        },
    )

    unsupported = [col["name"] for col in columns if col.get("automation")]
    if unsupported:
        print(
            "⚠️  Automation settings for columns are not yet supported via the GitHub API. "
            f"Skipped: {', '.join(unsupported)}",
            file=sys.stderr,
        )


def ensure_single_select_field(project_id: str, existing: Optional[FieldInfo], name: str, options: List[str]) -> None:
    payload_options = [{"name": opt} for opt in options if opt]
    if not payload_options:
        return

    mutation = """
    mutation($projectId: ID!, $fieldId: ID, $name: String!, $options: [ProjectV2SingleSelectFieldOptionInput!]!) {
      updateProjectV2Field(input: {
        projectId: $projectId,
        fieldId: $fieldId,
        name: $name,
        singleSelectOptions: $options
      }) {
        projectV2Field { id }
      }
    }
    """

    if existing and existing.typename == "ProjectV2SingleSelectField":
        graphql(
            mutation,
            {
                "projectId": project_id,
                "fieldId": existing.field_id,
                "name": name,
                "options": payload_options,
            },
        )
        return

    create_mutation = """
    mutation($input: CreateProjectV2FieldInput!) {
      createProjectV2Field(input: $input) {
        projectV2Field { id }
      }
    }
    """
    graphql(
        create_mutation,
        {
            "input": {
                "projectId": project_id,
                "name": name,
                "dataType": "SINGLE_SELECT",
                "singleSelectOptions": payload_options,
            }
        },
    )


def ensure_iteration_field(project_id: str, existing: Optional[FieldInfo], name: str, duration: int, start_day: str) -> None:
    if existing:
        return  # Iteration field updates are not yet supported; keep existing configuration.

    start_day_upper = start_day.upper()
    mutation = """
    mutation($input: CreateProjectV2IterationFieldInput!) {
      createProjectV2IterationField(input: $input) {
        projectV2IterationField { id }
      }
    }
    """
    graphql(
        mutation,
        {
            "input": {
                "projectId": project_id,
                "name": name,
                "duration": duration,
                "startDay": start_day_upper,
            }
        },
    )


def configure_custom_fields(project_id: str, fields: Dict[str, FieldInfo], blueprint: Dict[str, Any]) -> None:
    custom_fields = blueprint.get("customFields", [])
    for field in custom_fields:
        name = field.get("name")
        if not name:
            continue
        field_type = (field.get("type") or "").lower()
        existing = fields.get(name)

        if field_type == "single_select":
            ensure_single_select_field(
                project_id,
                existing,
                name,
                [str(option) for option in field.get("options", [])],
            )
        elif field_type == "iteration":
            duration = int(field.get("duration", 7))
            start_day = str(field.get("startDay", "MONDAY"))
            ensure_iteration_field(project_id, existing, name, duration, start_day)
        else:
            print(
                f"⚠️  Unsupported custom field type '{field_type}' for field '{name}'. Skipping.",
                file=sys.stderr,
            )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True, help="Login of the user or organization owning the project")
    parser.add_argument("--title", required=True, help="Title for the project board")
    parser.add_argument("--blueprint", required=True, help="Path to the blueprint JSON file")
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    ensure_gh_available()
    try:
        ensure_scopes(REQUIRED_SCOPES)
    except CLIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    try:
        blueprint = load_blueprint(args.blueprint)
    except CLIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    try:
        project = ensure_project(args.owner, args.title)
    except CLIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4

    print(f"✅ Using project at {project.url}")

    description = blueprint.get("description")
    if description:
        try:
            update_description(project.project_id, description)
            print("→ Updated project description")
        except CLIError as exc:
            print(f"⚠️  Failed to update description: {exc}", file=sys.stderr)

    try:
        fields = fetch_fields(project.project_id)
    except CLIError as exc:
        print(f"ERROR: Unable to fetch project fields: {exc}", file=sys.stderr)
        return 5

    columns = blueprint.get("columns", [])
    if columns:
        try:
            update_status_field(project.project_id, fields, columns)
            print("→ Configured status columns")
        except CLIError as exc:
            print(f"⚠️  Failed to configure status columns: {exc}", file=sys.stderr)

    try:
        configure_custom_fields(project.project_id, fields, blueprint)
    except CLIError as exc:
        print(f"⚠️  Failed to configure custom fields: {exc}", file=sys.stderr)

    if blueprint.get("labelColumnMapping"):
        print(
            "⚠️  Label to column automation is not yet exposed via the GitHub API; skipped mapping.",
            file=sys.stderr,
        )

    if blueprint.get("notes"):
        print(
            "ℹ️  Blueprint notes:\n  - "
            + "\n  - ".join(str(note) for note in blueprint["notes"]),
            file=sys.stderr,
        )

    print("🎯 Blueprint application complete. Project URL:")
    print(project.url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
