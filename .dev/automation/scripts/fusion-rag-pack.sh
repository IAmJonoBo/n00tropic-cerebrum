#!/usr/bin/env bash
set -euo pipefail

# Surface the freshest fusion export as a RAG-ready pack for agents.

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
EXPORT_ROOT="$ROOT/n00clear-fusion/exports"
ARTIFACT_DIR="$ROOT/.dev/automation/artifacts"
REPORT_FILE="$ARTIFACT_DIR/rag-pack-latest.json"

# Ensure pinned Node when used by Node consumers
# shellcheck source=/dev/null
source "$ROOT/scripts/ensure-nvm-node.sh" 2>/dev/null || true

mkdir -p "$ARTIFACT_DIR"

generated_at=$(
	python3 - <<'PY'
import datetime
print(datetime.datetime.now().isoformat())
PY
)

if [[ ! -d $EXPORT_ROOT ]]; then
	echo "[fusion-rag-pack] No exports directory at $EXPORT_ROOT" >&2
	exit 1
fi

latest_file=$(find "$EXPORT_ROOT" -type f -maxdepth 2 -print0 | xargs -0 ls -t | head -n1 || true)

if [[ -z $latest_file ]]; then
	echo "[fusion-rag-pack] No export files found under $EXPORT_ROOT" >&2
	exit 1
fi

mtime=$(
	env FILE="$latest_file" python3 - <<'PY'
import os, datetime
fname = os.environ["FILE"]
st = os.stat(fname)
print(datetime.datetime.fromtimestamp(st.st_mtime).isoformat())
PY
)
rel_path=${latest_file#"$ROOT/"}

cat >"$REPORT_FILE" <<JSON
{
  "generated_at": "$generated_at",
  "latest_export": "$rel_path",
  "last_modified": "$mtime",
  "note": "Mount this file into RAG runtimes; produced by fusion pipelines"
}
JSON

echo "[fusion-rag-pack] Published $rel_path -> $REPORT_FILE"
printf '{"status":"ok","artifact":"%s"}\n' "$REPORT_FILE"
