#!/usr/bin/env bash
set -euo pipefail

# Local preflight automation to mirror the core guardrails:
# - nvm pin, nvmrc sync
# - tokens presence + orchestration + drift
# - policy sync (check mode)
# - workspace graph export
# - Typesense freshness

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

# Flags: set to 1 to skip
SKIP_TOKENS=${SKIP_TOKENS:-0}
SKIP_POLICY=${SKIP_POLICY:-0}
SKIP_TYPESENSE=${SKIP_TYPESENSE:-0}

cleanup_validation_artifacts() {
	if [[ -x "$ROOT_DIR/scripts/cleanup-validation-artifacts.sh" ]]; then
		bash "$ROOT_DIR/scripts/cleanup-validation-artifacts.sh" || true
	fi
}

# Ensure Node pin
source "$ROOT_DIR/scripts/ensure-nvm-node.sh" 2>/dev/null || true

echo "[local-preflight] Syncing .nvmrc links"
bash "$ROOT_DIR/.dev/automation/scripts/sync-nvmrc.sh" --force

if [[ $SKIP_TOKENS -eq 0 ]]; then
	echo "[local-preflight] Checking tokens presence"
	bash "$ROOT_DIR/scripts/check-tokens-present.sh"

	echo "[local-preflight] Running tokens:orchestrate"
	pnpm -C "$ROOT_DIR/n00plicate" tokens:orchestrate

	echo "[local-preflight] Running tokens:validate (placeholder bypass allowed)"
	pnpm -C "$ROOT_DIR/n00plicate" tokens:validate || true

	echo "[local-preflight] Running tokens drift guard"
	bash "$ROOT_DIR/.dev/automation/scripts/token-drift.sh"
else
	echo "[local-preflight] Skipping token pipeline (SKIP_TOKENS=1)"
fi

if [[ $SKIP_POLICY -eq 0 ]]; then
	echo "[local-preflight] Running policy-sync --check"
	bash "$ROOT_DIR/.dev/automation/scripts/policy-sync.sh" --check
else
	echo "[local-preflight] Skipping policy-sync (SKIP_POLICY=1)"
fi

echo "[local-preflight] Exporting workspace graph"
bash "$ROOT_DIR/scripts/workspace-graph-export.sh"

echo "[local-preflight] Publishing dashboard artifacts (n00HQ Resources)"
bash "$ROOT_DIR/scripts/publish-dashboard-artifacts.sh"

if [[ $SKIP_TYPESENSE -eq 0 ]]; then
	echo "[local-preflight] Checking Typesense freshness"
	bash "$ROOT_DIR/.dev/automation/scripts/typesense-freshness.sh" 7
else
	echo "[local-preflight] Skipping Typesense freshness (SKIP_TYPESENSE=1)"
fi

cleanup_validation_artifacts

echo "[local-preflight] Done"
