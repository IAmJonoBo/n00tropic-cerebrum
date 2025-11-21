#!/usr/bin/env bash
set -uo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
SCRIPTS_DIR="$ROOT/.dev/automation/scripts"
MODE="check"

while [[ $# -gt 0 ]]; do
  case $1 in
    --mode=fix)
      MODE="fix"
      ;;
    --mode=check)
      MODE="check"
      ;;
    --fix)
      MODE="fix"
      ;;
    --check)
      MODE="check"
      ;;
    *)
      echo "[doctor] Unknown argument: $1" >&2
      exit 2
      ;;
  esac
  shift
done

STATUS=0

log() {
  printf '[doctor] %s\n' "$1"
}

check_token() {
  local secret_file="$ROOT/.secrets/renovate/config.js"
  if [[ ! -f "$secret_file" ]]; then
    log "❌ Renovate token file missing at .secrets/renovate/config.js"
    STATUS=1
    return
  fi
  local token
  token=$(grep -Eo 'RENO[VATE_]*TOKEN\s*=\s*"([^"]+)"' "$secret_file" | sed -E 's/^[^"]+"([^"]+)"/\1/')
  if [[ -z "$token" ]]; then
    log "❌ Renovate token could not be parsed from $secret_file"
    STATUS=1
    return
  fi
  if [[ ${#token} -lt 40 ]]; then
    log "⚠️  Renovate token looks suspiciously short; verify it has repo scope."
    STATUS=1
    return
  fi
  if [[ "$token" == "BeatenEggs1!" ]]; then
    log "❌ Placeholder Renovate token detected; update .secrets/renovate/config.js"
    STATUS=1
    return
  fi
  log "✅ Renovate token present."
}

sync_trunk() {
  if [[ ! -x "$SCRIPTS_DIR/sync-trunk-configs.sh" ]]; then
    log "⚠️  sync-trunk-configs.sh missing; skipping Trunk sync."
    STATUS=1
    return
  fi
  if [[ "$MODE" == "fix" ]]; then
    if "$SCRIPTS_DIR/sync-trunk-configs.sh" --write >/dev/null; then
      log "✅ Canonical Trunk configuration propagated."
    else
      log "❌ Failed to sync Trunk configuration."
      STATUS=1
    fi
  else
    if "$SCRIPTS_DIR/sync-trunk-configs.sh" --check >/dev/null; then
      log "✅ Trunk configuration already aligned."
    else
      log "⚠️  Trunk configuration drift detected (run with --fix)."
      STATUS=1
    fi
  fi
}

ensure_example_dependencies() {
  local example_dir="$ROOT/n00-frontiers/examples/projects/express-user-api"
  if [[ ! -d "$example_dir" ]]; then
    return
  fi
  if [[ -d "$example_dir/node_modules" && "$MODE" != "fix" ]]; then
    log "✅ express-user-api dependencies already installed."
    return
  fi
  if command -v pnpm >/dev/null 2>&1; then
    if (cd "$example_dir" && pnpm install --ignore-scripts >/dev/null); then
      log "✅ express-user-api dependencies installed/up to date."
    else
      log "❌ Failed to install express-user-api dependencies."
      STATUS=1
    fi
  else
    log "⚠️  pnpm not available; cannot ensure express-user-api dependencies."
    STATUS=1
  fi
}

ensure_n00t_dependencies() {
  local workspace_dir="$ROOT/n00t"
  if [[ ! -d "$workspace_dir" ]]; then
    return
  fi
  if [[ -d "$workspace_dir/node_modules" && "$MODE" != "fix" ]]; then
    log "✅ n00t workspace dependencies present."
    return
  fi
  if command -v pnpm >/dev/null 2>&1; then
    if (cd "$workspace_dir" && pnpm install --ignore-scripts >/dev/null); then
      log "✅ n00t workspace dependencies installed."
    else
      log "❌ Failed to install n00t workspace dependencies."
      STATUS=1
    fi
  else
    log "⚠️  pnpm not available; cannot install n00t dependencies."
    STATUS=1
  fi
}

refresh_dashboard() {
  if [[ -x "$SCRIPTS_DIR/generate-renovate-dashboard.py" ]]; then
    if python3 "$SCRIPTS_DIR/generate-renovate-dashboard.py" >/dev/null; then
      log "✅ Renovate dashboard refreshed."
    else
      log "❌ Failed to refresh Renovate dashboard."
      STATUS=1
    fi
  fi
}

check_token
sync_trunk
ensure_example_dependencies
ensure_n00t_dependencies
refresh_dashboard

if [[ $STATUS -eq 0 ]]; then
  log "Doctor checks complete."
else
  log "Doctor encountered issues."
fi

exit $STATUS
