#!/usr/bin/env bash
set -uo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
SCRIPTS_DIR="$ROOT/.dev/automation/scripts"

log() {
  printf '[refresh-workspace] %s\n' "$1"
}

STARTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
FAILED=0
UPDATED=()
FAILED_REPOS=()

update_repo() {
  local dir="$1"
  if [[ ! -d "$ROOT/$dir/.git" ]]; then
    log "Skipping $dir (not a git repository)"
    return
  fi
  log "Updating $dir"
  if (cd "$ROOT/$dir" && git fetch --all --prune && git pull --ff-only); then
    UPDATED+=("$dir")
  else
    log "⚠️  Fast-forward failed in $dir; manual intervention required."
    FAILED=1
    FAILED_REPOS+=("$dir")
  fi
}

log "Refreshing workspace repositories"

update_repo "n00-frontiers"
update_repo "n00-cortex"
update_repo "n00t"
update_repo "n00tropic"
update_repo "n00plicate"

if [[ -f "$ROOT/.gitmodules" ]]; then
  log "Updating submodules"
  if ! (cd "$ROOT" && git submodule update --init --recursive --remote); then
    log "⚠️  Submodule update encountered errors."
    FAILED=1
    FAILED_REPOS+=("submodules")
  fi
fi

if [[ $FAILED -eq 0 ]]; then
  log "✅ Workspace refresh complete"
else
  log "⚠️  Workspace refresh completed with issues"
fi

COMPLETED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [[ -f "$SCRIPTS_DIR/record-capability-run.py" ]]; then
  STATUS=$([[ $FAILED -eq 0 ]] && echo "succeeded" || echo "failed")
  SUMMARY=$([[ $FAILED -eq 0 ]] && echo "Fast-forwarded ${#UPDATED[@]} repositories" || echo "Issues in ${FAILED_REPOS[*]}")
  python3 "$SCRIPTS_DIR/record-capability-run.py" \
    --capability "workspace.refresh" \
    --status "$STATUS" \
    --summary "$SUMMARY" \
    --started "$STARTED_AT" \
    --completed "$COMPLETED_AT"
fi

if [[ $FAILED -ne 0 ]]; then
  exit 1
fi
