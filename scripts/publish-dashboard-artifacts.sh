#!/usr/bin/env bash
set -euo pipefail

# Copy latest workspace graph + capability health into n00HQ Resources for local UI/dev preview.

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ARTIFACT_DIR="$ROOT_DIR/.dev/automation/artifacts"
DEST_DIR="$ROOT_DIR/n00HQ/Resources/data"

mkdir -p "$DEST_DIR"

GRAPH_SRC="$ARTIFACT_DIR/workspace-graph.json"
HEALTH_SRC="$ARTIFACT_DIR/capability-health.json"
RUNS_JSON="$ARTIFACT_DIR/automation/agent-runs.json"
RUNS_JSONL="$ARTIFACT_DIR/automation/run-envelopes.jsonl"
TOKEN_DRIFT="$ARTIFACT_DIR/token-drift.json"

if [[ ! -f $GRAPH_SRC || ! -f $HEALTH_SRC ]]; then
	echo "[publish-dashboard] Graph or capability health artifacts missing; run scripts/workspace-graph-export.sh first." >&2
	exit 1
fi

cp "$GRAPH_SRC" "$DEST_DIR/graph.json"
cp "$HEALTH_SRC" "$DEST_DIR/capability-health.json"
if [[ -f $RUNS_JSON ]]; then cp "$RUNS_JSON" "$DEST_DIR/agent-runs.json"; fi
if [[ -f $RUNS_JSONL ]]; then cp "$RUNS_JSONL" "$DEST_DIR/run-envelopes.jsonl"; fi
if [[ -f $TOKEN_DRIFT ]]; then cp "$TOKEN_DRIFT" "$DEST_DIR/token-drift.json"; fi

echo "[publish-dashboard] Copied graph + health to n00HQ/Resources/data"
