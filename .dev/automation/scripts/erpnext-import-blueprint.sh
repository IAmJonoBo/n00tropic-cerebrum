#!/usr/bin/env python3
"""Import an ERPNext project blueprint via the public REST API.

The script is intentionally idempotent: it creates the target Project when
missing and updates its description/tags on subsequent runs. Task subjects are
treated as stable identifiers under the target Project; matching tasks are
updated in place while new entries are created as needed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.parse
import urllib.request


SUMMARY_PATH = Path("/tmp/erpnext_import_resp.json")
VALID_TASK_PRIORITIES = {"Low", "Medium", "High", "Urgent"}


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description="Import a project blueprint into ERPNext via REST."
  )
  parser.add_argument(
    "--instance",
    required=True,
    help="Base URL of the ERPNext instance, e.g. https://erpnext.local",
  )
  parser.add_argument(
    "--site",
    help="Site name when running a multi-tenant bench (sent as X-Frappe-Site-Name)",
  )
  parser.add_argument(
    "--blueprint",
    required=True,
    help="Path to the project blueprint (JSON by default, YAML supported when PyYAML is installed)",
  )
  return parser.parse_args()


def load_blueprint(path: str) -> Dict[str, Any]:
  blueprint_path = Path(path)
  if not blueprint_path.is_file():
    raise SystemExit(f"ERROR: Blueprint not found: {path}")

  data_text = blueprint_path.read_text(encoding="utf-8")
  suffix = blueprint_path.suffix.lower()

  if suffix in {".yaml", ".yml"}:
    try:
      import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
      raise SystemExit(
        "ERROR: PyYAML is required to parse YAML blueprints. Install it or provide a JSON file."
      ) from exc
    data = yaml.safe_load(data_text)
  else:
    try:
      data = json.loads(data_text)
    except json.JSONDecodeError as exc:
      raise SystemExit(f"ERROR: {path} is not valid JSON: {exc}") from exc

  if not isinstance(data, dict):
    raise SystemExit("ERROR: Blueprint must decode to a JSON/YAML object.")

  return data


def to_yes_no(value: Any, default: str = "Yes") -> str:
  if value is None:
    return default
  if isinstance(value, bool):
    return "Yes" if value else "No"
  text = str(value).strip().lower()
  if text in {"yes", "true", "1", "active", "open"}:
    return "Yes"
  if text in {"no", "false", "0", "inactive", "closed"}:
    return "No"
  return default


def normalise_project_status(raw: Optional[str]) -> str:
  if not raw:
    return "Open"
  mapping = {
    "planned": "Open",
    "planning": "Open",
    "not started": "Open",
    "in progress": "Open",
    "working": "Open",
    "active": "Open",
    "complete": "Completed",
    "completed": "Completed",
    "done": "Completed",
    "closed": "Completed",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
  }
  status = mapping.get(raw.strip().lower(), raw.strip())
  if status not in {"Open", "Completed", "Cancelled"}:
    return "Open"
  return status


def normalise_task_priority(raw: Any) -> str:
  if raw is None:
    return "Medium"
  priority = str(raw).strip().title()
  if priority not in VALID_TASK_PRIORITIES:
    return "Medium"
  return priority


def build_project_payload(data: Dict[str, Any]) -> Dict[str, Any]:
  project_name = data.get("project_name")
  if not project_name:
    raise SystemExit("ERROR: Blueprint is missing 'project_name'.")

  project_code = data.get("project_code")
  display_name = project_name
  if project_code and project_code not in project_name:
    display_name = f"{project_code} - {project_name}"

  payload: Dict[str, Any] = {
    "project_name": display_name,
    "status": normalise_project_status(data.get("status")),
    "is_active": to_yes_no(data.get("is_active"), "Yes"),
  }

  description = (data.get("description") or "").strip()
  if description:
    payload["project_detail"] = description

  tags = data.get("tag_defaults") or []
  if tags:
    payload["_user_tags"] = ", ".join(str(tag) for tag in tags)

  return payload


def build_task_payloads(data: Dict[str, Any]) -> List[Dict[str, Any]]:
  tasks: List[Dict[str, Any]] = []
  for group in data.get("task_groups", []) or []:
    if not isinstance(group, dict):
      continue
    group_name = str(group.get("name") or "General").strip() or "General"
    sla_days = group.get("sla_days")
    for index, entry in enumerate(group.get("tasks", []) or [], start=1):
      if not isinstance(entry, dict):
        continue
      title = entry.get("title") or f"Task {index}"
      subject = f"{group_name}: {title}"
      description = (entry.get("description") or "").strip()

      desc_sections: List[str] = []
      if description:
        desc_sections.append(description)

      meta_lines = [f"Blueprint group: {group_name}"]
      if sla_days not in (None, ""):
        meta_lines.append(f"SLA target: {sla_days} day(s)")
      desc_sections.append("\n".join(meta_lines))

      tasks.append(
        {
          "subject": subject,
          "description": "\n\n".join(filter(None, desc_sections)),
          "priority": normalise_task_priority(entry.get("priority")),
        }
      )

  return tasks


def build_headers(args: argparse.Namespace) -> Dict[str, str]:
  bearer = os.getenv("ERPNEXT_BEARER_TOKEN")
  api_key = os.getenv("ERPNEXT_API_KEY")
  api_secret = os.getenv("ERPNEXT_API_SECRET")

  if bearer:
    auth_value = f"token {bearer}"
  elif api_key and api_secret:
    auth_value = f"token {api_key}:{api_secret}"
  else:
    raise SystemExit(
      "ERROR: Set ERPNEXT_BEARER_TOKEN or ERPNEXT_API_KEY/ERPNEXT_API_SECRET before running."
    )

  headers = {"Authorization": auth_value}
  if args.site:
    headers["X-Frappe-Site-Name"] = args.site

  return headers


def unwrap(response: Any) -> Any:
  if isinstance(response, dict):
    if "data" in response:
      return response["data"]
    if "message" in response:
      return response["message"]
  return response


class ERPNextClient:
  def __init__(self, base_url: str, headers: Dict[str, str]):
    self.base_url = base_url.rstrip("/") + "/"
    self.headers = headers

  def _build_url(self, route: str, params: Optional[Dict[str, str]] = None) -> str:
    route_path = route.lstrip("/")
    url = urllib.parse.urljoin(self.base_url, route_path)
    if params:
      query = urllib.parse.urlencode(params)
      url = url + ("&" if "?" in url else "?") + query
    return url

  def _request(
    self,
    method: str,
    route: str,
    params: Optional[Dict[str, str]] = None,
    payload: Optional[Dict[str, Any]] = None,
  ) -> Any:
    url = self._build_url(route, params)
    headers = dict(self.headers)
    data_bytes: Optional[bytes] = None
    if payload is not None:
      data_bytes = json.dumps(payload).encode("utf-8")
      headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
    try:
      with urllib.request.urlopen(request) as response:
        raw = response.read()
    except urllib.error.HTTPError as exc:
      body = exc.read().decode("utf-8", "replace")
      raise RuntimeError(f"{method} {url} failed ({exc.code}): {body}") from None

    if not raw:
      return {}

    try:
      return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
      raise RuntimeError(f"Failed to decode ERPNext response from {url}: {raw!r}") from exc

  def get(self, route: str, params: Optional[Dict[str, str]] = None) -> Any:
    return self._request("GET", route, params=params)

  def post(self, route: str, payload: Dict[str, Any]) -> Any:
    return self._request("POST", route, payload=payload)

  def put(self, route: str, payload: Dict[str, Any]) -> Any:
    return self._request("PUT", route, payload=payload)


def quote_name(name: str) -> str:
  return urllib.parse.quote(name, safe="")


def find_existing_project(client: ERPNextClient, display_name: str) -> Optional[Dict[str, Any]]:
  filters = json.dumps([["project_name", "=", display_name]])
  fields = json.dumps(["name", "project_name", "status"])
  response = unwrap(
    client.get(
      "api/resource/Project",
      params={
        "filters": filters,
        "fields": fields,
        "limit_page_length": "1",
      },
    )
  )
  if isinstance(response, list) and response:
    project = response[0]
    full_details = unwrap(
      client.get(
        f"api/resource/Project/{quote_name(project['name'])}",
        params={"fields": json.dumps(["name", "project_name", "status", "project_detail"])}
      )
    )
    if isinstance(full_details, dict):
      return full_details
    return project
  return None


def create_project(client: ERPNextClient, payload: Dict[str, Any]) -> Dict[str, Any]:
  response = unwrap(client.post("api/resource/Project", {"doctype": "Project", **payload}))
  if not isinstance(response, dict) or "name" not in response:
    raise RuntimeError(f"Unexpected response while creating project: {response}")
  return response


def update_project(client: ERPNextClient, name: str, payload: Dict[str, Any]) -> None:
  client.put(f"api/resource/Project/{quote_name(name)}", payload)


def find_existing_task(client: ERPNextClient, project_name: str, subject: str) -> Optional[Dict[str, Any]]:
  filters = json.dumps([
    ["project", "=", project_name],
    ["subject", "=", subject],
  ])
  fields = json.dumps(["name", "subject", "priority", "project"])
  response = unwrap(
    client.get(
      "api/resource/Task",
      params={
        "filters": filters,
        "fields": fields,
        "limit_page_length": "1",
      },
    )
  )
  if isinstance(response, list) and response:
    return response[0]
  return None


def fetch_task_details(client: ERPNextClient, name: str) -> Dict[str, Any]:
  fields = json.dumps(["name", "description", "priority", "status", "project"])
  response = unwrap(client.get(f"api/resource/Task/{quote_name(name)}", params={"fields": fields}))
  if not isinstance(response, dict):
    raise RuntimeError(f"Unexpected task response for {name}: {response}")
  return response


def create_task(client: ERPNextClient, project_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
  task_payload = {"doctype": "Task", "project": project_name, "status": "Open", **payload}
  response = unwrap(client.post("api/resource/Task", task_payload))
  if not isinstance(response, dict) or "name" not in response:
    raise RuntimeError(f"Unexpected response while creating task: {response}")
  return response


def update_task(client: ERPNextClient, name: str, payload: Dict[str, Any]) -> None:
  client.put(f"api/resource/Task/{quote_name(name)}", payload)


def main() -> None:
  args = parse_args()
  blueprint = load_blueprint(args.blueprint)

  headers = build_headers(args)
  client = ERPNextClient(args.instance, headers)

  project_payload = build_project_payload(blueprint)
  display_name = project_payload["project_name"]
  task_payloads = build_task_payloads(blueprint)

  summary: Dict[str, Any] = {
    "project": {},
    "tasks": {"created": [], "updated": [], "unchanged": []},
    "notes": blueprint.get("notes") or [],
  }

  try:
    existing_project = find_existing_project(client, display_name)
    if existing_project:
      update_project(client, existing_project["name"], project_payload)
      project_name = existing_project["name"]
      summary["project"] = {"name": project_name, "action": "updated"}
      print(f"Project '{display_name}' already exists (name={project_name}); fields updated.")
    else:
      created_project = create_project(client, project_payload)
      project_name = created_project["name"]
      summary["project"] = {"name": project_name, "action": "created"}
      print(f"Created project '{display_name}' (name={project_name}).")

    for task in task_payloads:
      subject = task["subject"]
      existing_task = find_existing_task(client, project_name, subject)
      if existing_task:
        details = fetch_task_details(client, existing_task["name"])
        updates: Dict[str, Any] = {}

        if (details.get("description") or "").strip() != task["description"].strip():
          updates["description"] = task["description"]

        current_priority = normalise_task_priority(details.get("priority"))
        desired_priority = normalise_task_priority(task.get("priority"))
        if current_priority != desired_priority:
          updates["priority"] = desired_priority

        if updates:
          update_task(client, existing_task["name"], updates)
          summary["tasks"]["updated"].append({
            "name": existing_task["name"],
            "subject": subject,
          })
          print(f"Updated task '{subject}' (name={existing_task['name']}).")
        else:
          summary["tasks"]["unchanged"].append({
            "name": existing_task["name"],
            "subject": subject,
          })
          print(f"Task '{subject}' already up to date (name={existing_task['name']}).")
      else:
        created_task = create_task(client, project_name, task)
        summary["tasks"]["created"].append({
          "name": created_task["name"],
          "subject": subject,
        })
        print(f"Created task '{subject}' (name={created_task['name']}).")

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Summary written to {SUMMARY_PATH}.")

    if summary["notes"]:
      print("\nBlueprint notes:")
      for note in summary["notes"]:
        print(f"- {note}")

  except RuntimeError as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc


if __name__ == "__main__":
  main()
