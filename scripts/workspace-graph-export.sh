#!/usr/bin/env bash
set -euo pipefail

# Export a consolidated workspace graph and capability health report.
# - Graph is produced by n00-cortex/scripts/build-graph.mjs (already pulls templates, schemas, corpora, capabilities, runs).
# - Capability health checks for missing/broken entrypoints in n00t/capabilities/manifest.json.

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ARTIFACT_DIR="$ROOT_DIR/.dev/automation/artifacts"
GRAPH_OUT="$ARTIFACT_DIR/workspace-graph.json"
CAP_HEALTH_OUT="$ARTIFACT_DIR/capability-health.json"

# Ensure pinned Node version
if [[ -f "$ROOT_DIR/scripts/ensure-nvm-node.sh" ]]; then
	# shellcheck source=/dev/null
	source "$ROOT_DIR/scripts/ensure-nvm-node.sh"
fi

mkdir -p "$ARTIFACT_DIR"

export GRAPH_OUTPUT="$GRAPH_OUT"

echo "[workspace-graph] Building graph -> $GRAPH_OUTPUT"
node "$ROOT_DIR/n00-cortex/scripts/build-graph.mjs" "$@"

echo "[workspace-graph] Checking capability entrypoints -> $CAP_HEALTH_OUT"
node "$ROOT_DIR/scripts/capability-health.mjs" --output "$CAP_HEALTH_OUT"

echo "[workspace-graph] Done"
printf '{"status":"ok","graphPath":"%s","healthPath":"%s"}\n' "$GRAPH_OUT" "$CAP_HEALTH_OUT"
