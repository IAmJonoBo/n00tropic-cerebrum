#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: github-project-apply-blueprint.sh --owner ORG --title "Project Title" [--blueprint path/to/blueprint.json] [--template-number N] [--source-owner ORG]

Creates a GitHub project from an existing template project (copy) or, when available, a blueprint file.
Automatically supplies the required --title flag so `gh project copy` does not fail with "required flag(s) \"title\" not set".

Environment:
  GH_TOKEN / GITHUB_TOKEN should be set if your CLI is not already authenticated.

Examples:
  # Copy from existing project number 42
  .dev/automation/scripts/github-project-apply-blueprint.sh \
    --owner IAmJonoBo \
    --title "Unified PM – Frontier Ops Control Plane" \
    --template-number 42 \
    --source-owner IAmJonoBo

  # Provide metadata via blueprint JSON (optional keys: template_project_number, template_owner)
  .dev/automation/scripts/github-project-apply-blueprint.sh \
    --owner IAmJonoBo \
    --title "Unified PM – Frontier Ops Control Plane" \
    --blueprint n00tropic-cerebrum/n00-frontiers/templates/project-management/{{cookiecutter.project_slug}}/blueprints/github-project-template.json
USAGE
  exit "${1:-1}"
}

OWNER=""
TITLE=""
BLUEPRINT=""
TEMPLATE_NUMBER=""
SOURCE_OWNER=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --owner)
      OWNER="${2:-}"
      shift 2
      ;;
    --template-number)
      TEMPLATE_NUMBER="${2:-}"
      shift 2
      ;;
    --source-owner)
      SOURCE_OWNER="${2:-}"
      shift 2
      ;;
    --title)
      TITLE="${2:-}"
      shift 2
      ;;
    --blueprint)
      BLUEPRINT="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage 1
      ;;
  esac
done

if [[ -z "$OWNER" || -z "$TITLE" ]]; then
  echo "ERROR: --owner and --title are required." >&2
  usage 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI (gh) not found. Install or ensure it is on PATH." >&2
  exit 2
fi

if [[ -n "$BLUEPRINT" ]]; then
  ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
  BLUEPRINT_PATH="$BLUEPRINT"
  if [[ ! -f "$BLUEPRINT_PATH" ]]; then
    BLUEPRINT_PATH="$ROOT/$BLUEPRINT"
  fi
  if [[ ! -f "$BLUEPRINT_PATH" ]]; then
    echo "ERROR: Blueprint file not found at $BLUEPRINT or $BLUEPRINT_PATH." >&2
    exit 3
  fi
  mapfile -t TEMPLATE_META < <(python3 - "$BLUEPRINT_PATH" <<'PY'
import json
import sys
try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    data = {}
print(data.get("template_project_number") or "")
print(data.get("template_owner") or "")
PY
  )
  TEMPLATE_NUMBER="${TEMPLATE_NUMBER:-${TEMPLATE_META[0]}}"
  SOURCE_OWNER="${SOURCE_OWNER:-${TEMPLATE_META[1]}}"
fi

SOURCE_OWNER="${SOURCE_OWNER:-$OWNER}"

if [[ -z "$TEMPLATE_NUMBER" ]]; then
  echo "⚠️  No template project number provided; falling back to plain 'gh project create'. Blueprint structure must be applied manually."
  if ! PROJECT_URL=$(gh project create --owner "$OWNER" --title "$TITLE" --format json --jq '.url' 2>&1); then
    echo "❌ Failed to create project. Output from gh:" >&2
    echo "$PROJECT_URL" >&2
    exit 4
  fi
  echo "✅ GitHub project created: $PROJECT_URL"
  echo "ℹ️  Apply workflow/field configuration manually per blueprint instructions."
  exit 0
fi

echo "Copying project template #$TEMPLATE_NUMBER from '$SOURCE_OWNER' to '$OWNER' with title '$TITLE'..."
if ! PROJECT_URL=$(gh project copy "$TEMPLATE_NUMBER" --source-owner "$SOURCE_OWNER" --target-owner "$OWNER" --title "$TITLE" --format json --jq '.url' 2>&1); then
  echo "❌ Failed to copy project. Output from gh:" >&2
  echo "$PROJECT_URL" >&2
  echo "Hint: ensure the template project exists and your token has access." >&2
  exit 4
fi

echo "✅ GitHub project created: $PROJECT_URL"
echo "$PROJECT_URL"
