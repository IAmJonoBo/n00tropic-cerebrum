#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
RUNNER_DIR="$ROOT/actions-runner"

log(){ printf '[runner-doctor] %s\n' "$*"; }

if [[ ! -d "$RUNNER_DIR" ]]; then
  log "actions-runner directory not found at $RUNNER_DIR"
  exit 1
fi

log "Runner dir: $RUNNER_DIR"

if [[ -x "$RUNNER_DIR/bin/Runner.Listener" ]]; then
  ver=$("$RUNNER_DIR/bin/Runner.Listener" --version 2>/dev/null || true)
  log "Current runner version: ${ver:-unknown}"
else
  log "Runner.Listener binary not found"
fi

if command -v node >/dev/null 2>&1; then
  log "Node: $(node -v)"
fi
if command -v pnpm >/dev/null 2>&1; then
  log "pnpm: $(pnpm -v)"
fi
if command -v trunk >/dev/null 2>&1; then
  log "trunk: $(trunk --version 2>/dev/null | head -1)"
fi

if [[ -f "$RUNNER_DIR/.service" ]]; then
  log "Service config detected (.service)"
fi

log "Runner labels (if configured):"
if [[ -f "$RUNNER_DIR/.runner" ]]; then
  grep -E '"labels"' -A1 "$RUNNER_DIR/.runner" || true
else
  log " .runner file not present (run ./config.sh to register)"
fi

log "Checking disk space"
df -h "$RUNNER_DIR" | sed '1d' | while read line; do log " $line"; done

log "Checking cache sizes under _diag and _work"
for d in "_diag" "_work"; do
  if [[ -d "$RUNNER_DIR/$d" ]]; then
    size=$(du -sh "$RUNNER_DIR/$d" 2>/dev/null | awk '{print $1}')
    log " $d size: ${size}"
  fi
done

log "Done"
