#!/usr/bin/env bash
set -euo pipefail

# Orchestrate policy -> templates -> schemas -> docs -> release notes.
# Designed for both human use and n00t capability execution.

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
CORTEX_DIR="$ROOT/n00-cortex"
DOCS_DIR="$ROOT/n00menon"
RELEASE_SCRIPT="$ROOT/.dev/automation/scripts/workspace-release.sh"
INGEST_SCRIPT="$ROOT/.dev/automation/scripts/ingest-frontiers.sh"

# Ensure pinned Node version for downstream Node workflows
# shellcheck source=/dev/null
source "$ROOT/scripts/ensure-nvm-node.sh" 2>/dev/null || true

MODE="run"
if [[ ${1-} == "--check" ]]; then
	MODE="check"
fi

echo "[policy-sync] mode=$MODE"

echo "[policy-sync] Linking subrepo .nvmrc files to workspace pin"
bash "$ROOT/.dev/automation/scripts/sync-nvmrc.sh"

# 1) Ingest latest templates into cortex (derives schemas/manifests).
if [[ -x $INGEST_SCRIPT ]]; then
	[[ $MODE == "check" ]] && extra="--check" || extra=""
	bash "$INGEST_SCRIPT" $extra
else
	echo "[policy-sync] ingest script missing: $INGEST_SCRIPT" >&2
	exit 1
fi

# 2) Validate cortex schemas/data after ingest.
if [[ -d $CORTEX_DIR ]]; then
	pushd "$CORTEX_DIR" >/dev/null
	if [[ ! -d node_modules ]]; then
		echo "[policy-sync] Installing cortex deps (npm)"
		npm install --silent --no-progress
	fi
	if [[ $MODE == "check" ]]; then
		npm run validate:schemas --silent
	else
		npm run validate:schemas --silent
	fi
	popd >/dev/null
fi

# 3) Sync TechDocs/Antora content from cortex/frontiers into n00menon.
if [[ -d $DOCS_DIR ]]; then
	node "$ROOT/scripts/sync-n00menon-docs.mjs" --write
fi

# 4) Regenerate workspace release snapshot (writes 1. Cerebrum Docs/releases.yaml).
if [[ -x $RELEASE_SCRIPT ]]; then
	bash "$RELEASE_SCRIPT"
fi

echo "[policy-sync] done"
printf '{"status":"ok"}\n'
