#!/usr/bin/env bash
set -euo pipefail

# Detect design token drift across the superproject and emit an artifact summary.

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
N00PLICATE_DIR="$ROOT/n00plicate"
ARTIFACT_DIR="$ROOT/.dev/automation/artifacts"
STATE_FILE="$ARTIFACT_DIR/token-hash.txt"
REPORT_FILE="$ARTIFACT_DIR/token-drift.json"
TOKENS_PATH="$N00PLICATE_DIR/packages/design-tokens/libs/tokens/json/tokens.json"

# Ensure pinned Node version for validation steps
# shellcheck source=/dev/null
source "$ROOT/scripts/ensure-nvm-node.sh" 2>/dev/null || true

mkdir -p "$ARTIFACT_DIR"

echo "[token-drift] Computing current hash"
if [[ ! -f $TOKENS_PATH ]]; then
	echo "[token-drift] tokens.json missing at $TOKENS_PATH" >&2
	printf '{"status":"error","reason":"tokens_missing","tokens_path":"%s"}\n' "$TOKENS_PATH"
	exit 1
fi

current_hash=$(node "$N00PLICATE_DIR/scripts/hash-tokens.mjs")
previous_hash=""
drift="false"

if [[ -f $STATE_FILE ]]; then
	previous_hash=$(cat "$STATE_FILE")
	if [[ $previous_hash != "$current_hash" ]]; then
		drift="true"
	fi
else
	# First run, treat as baseline without flagging drift
	previous_hash="$current_hash"
fi

echo "$current_hash" >"$STATE_FILE"

validation="skipped"
validation_reason="TOKENS_SKIP_VALIDATE"

# Detect Node version mismatch (non-fatal; we still emit hash)
if [[ ${TOKENS_SKIP_VALIDATE:-0} == 1 ]]; then
	echo "[token-drift] Skipping token validation (TOKENS_SKIP_VALIDATE=1)"
elif node -e "require('./scripts/check-node-version.mjs')" >/dev/null 2>&1; then
	echo "[token-drift] Validating token contract (n00plicate)"
	if pnpm -C "$N00PLICATE_DIR" run tokens:validate >/dev/null; then
		validation="ok"
		validation_reason=""
	else
		validation="failed"
		validation_reason="token_validation_failed"
		echo "[token-drift] tokens:validate failed" >&2
	fi
else
	echo "[token-drift] Node version mismatch; skipping validation" >&2
	validation="skipped"
	validation_reason="node_version_mismatch"
fi

generated_at=$(
	python3 - <<'PY'
import datetime
print(datetime.datetime.now().isoformat())
PY
)

cat >"$REPORT_FILE" <<JSON
{
  "generated_at": "$generated_at",
  "current_hash": "$current_hash",
  "previous_hash": "$previous_hash",
  "drift": $drift,
  "tokens_path": "n00plicate/packages/design-tokens/libs/tokens/json/tokens.json",
  "validation": "$validation",
  "validation_reason": "$validation_reason"
}
JSON

echo "[token-drift] Drift=$drift -> $REPORT_FILE"
printf '{"status":"ok","artifact":"%s","drift":%s,"validation":"%s","validation_reason":"%s"}\n' "$REPORT_FILE" "$drift" "$validation" "$validation_reason"
