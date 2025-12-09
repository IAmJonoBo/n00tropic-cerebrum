#!/usr/bin/env bash
set -euo pipefail

# Control-tower orchestrated health run across the superrepo.
# Steps (fail-fast):
# 1) Check frontiers export freshness
# 2) Check cortex ingestion freshness
# 3) Run n00t tests (pnpm workspace)
# 4) Autofix metadata tags/links
# 5) Run full meta-check (doctor + auto-fix)

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# If invoked from inside a subrepo (e.g., n00-cortex), hop one level up to the workspace root
if [[ ! -d "$ROOT/n00-frontiers" && -d "$ROOT/../n00-frontiers" ]]; then
	ROOT="$(cd "$ROOT/.." && pwd)"
fi
cd "$ROOT"

log() { printf '\n[control-tower] %s\n' "$*"; }

ensure_uv() {
	if command -v uv >/dev/null 2>&1; then return; fi
	curl -LsSf https://astral.sh/uv/install.sh | sh
	export PATH="$HOME/.local/bin:$PATH"
}

ensure_uv
export UV_CACHE_DIR=${UV_CACHE_DIR:-"$ROOT/.cache/uv"}
# Ensure yaml for autofix script (idempotent)
uv pip install --quiet pyyaml >/dev/null 2>&1 || true

log "1/5 frontiers export --check"
if ! (cd "$ROOT/n00-frontiers" && uv run python tools/export_cortex_assets.py --check); then
	log "frontiers export drift detected; re-run tools/export_cortex_assets.py and commit"
	exit 1
fi

log "2/5 cortex ingest --check"
if ! (cd "$ROOT/n00-cortex" && node scripts/ingest-frontiers.mjs --check); then
	log "cortex ingest drift detected; run pnpm run ingest:frontiers and commit"
	exit 1
fi

log "3/5 n00t tests"
(cd "$ROOT/n00t" && pnpm test)

log "4/5 metadata autofix"
if [[ -x "$ROOT/.venv-workspace/bin/python" ]]; then
	"$ROOT/.venv-workspace/bin/python" "$ROOT/.dev/automation/scripts/autofix-project-metadata.py" --apply || true
else
	uv run --with pyyaml python "$ROOT/.dev/automation/scripts/autofix-project-metadata.py" --apply || true
fi

log "5/5 meta-check"
"$ROOT/.dev/automation/scripts/meta-check.sh" --doctor --auto-fix

log "Done"
