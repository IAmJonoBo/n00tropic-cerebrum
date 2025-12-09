#!/usr/bin/env bash
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
ART_DIR="$ROOT/.dev/automation/artifacts/automation"
mkdir -p "$ART_DIR"
TS=$(date -u +%Y%m%dT%H%M%SZ)
LOG="$ART_DIR/sync-ecosystem-$TS.json"

start_ts=$(date -u +%s)
status="ok"
message=""

run() {
	cmd="$1"
	echo "[sync] $cmd"
	if ! eval "$cmd"; then
		status="failed"
		message="command failed: $cmd"
	fi
}

run "cd '$ROOT/n00-frontiers' && python3 tools/export_cortex_assets.py"
run "cd '$ROOT/n00clear-fusion' && python3 scripts/export_cortex.py"
run "pnpm -C '$ROOT/n00-cortex' run ingest:frontiers"
run "pnpm -C '$ROOT/n00-cortex' run ingest:frontiers -- --update-lock --update-fusion-lock"
run "pnpm -C '$ROOT/n00-cortex' run export:assets"
run "pnpm -C '$ROOT/n00-cortex' run graph:build"
run "pnpm -C '$ROOT/n00-cortex' test"

if [ "$status" != "ok" ]; then
	message="failed step in sync; see logs above"
fi

end_ts=$(date -u +%s)
duration=$((end_ts - start_ts))
cat >"$LOG" <<JSON
{
  "started_at": "$TS",
  "status": "$status",
  "message": "$message",
  "duration_sec": $duration
}
JSON

echo "[sync] telemetry written to $LOG"

if [ "$status" != "ok" ]; then
	exit 1
fi
