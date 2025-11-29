#!/usr/bin/env bash
set -euo pipefail

# End-to-end pipeline validator for the superrepo and key subprojects.
# - Creates isolated temp fixtures (docs + PDF) so pipelines always have inputs.
# - Runs golden-path commands with per-step logs.
# - Summaries land in .dev/automation/artifacts/pipeline-validation/latest.json
# - Cleaning: --clean removes temp + old artifacts; auto-prunes stale runs.
#
# Usage: scripts/validate-pipelines.sh [--clean] [--list] [--skip <name>] [--only <name>]
# Pipelines: preflight, graph, docs, fusion

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ARTIFACT_DIR="$ROOT_DIR/.dev/automation/artifacts/pipeline-validation"
TMP_DIR="$ROOT_DIR/.dev/tmp/pipeline-validation"
export ROOT_DIR TMP_DIR
mkdir -p "$ARTIFACT_DIR" "$TMP_DIR"

SKIP_SET=()
ONLY_SET=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --clean)
      echo "[validate] Cleaning $TMP_DIR and old artifacts"
      rm -rf "$TMP_DIR"
      mkdir -p "$TMP_DIR"
      find "$ARTIFACT_DIR" -type f -mtime +7 -delete 2>/dev/null || true
      ;;
    --skip)
      SKIP_SET+=("$2"); shift
      ;;
    --only)
      ONLY_SET+=("$2"); shift
      ;;
    --list)
      echo "preflight graph docs fusion"
      exit 0
      ;;
    *)
      echo "Usage: $0 [--clean] [--list] [--skip name] [--only name]" >&2
      exit 1
      ;;
  esac
  shift
done

should_run() {
  local name="$1"
  if [[ ${#ONLY_SET[@]} -gt 0 ]]; then
    for o in "${ONLY_SET[@]}"; do [[ $o == "$name" ]] && return 0; done
    return 1
  fi
  for s in "${SKIP_SET[@]}"; do [[ $s == "$name" ]] && return 1; done
  return 0
}

stamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

log_step() {
  local name="$1"; shift
  local log_file="$ARTIFACT_DIR/${name}-$(date -u +%Y%m%dT%H%M%SZ).log"
  echo "[validate] >>> $name"
  local start_ns end_ns duration_ms status="ok"
  start_ns=$(python3 - <<'PY'
import time; print(int(time.time()*1_000_000_000))
PY
)
  if ! ( "$@" ) &> "$log_file"; then
    status="fail"
  fi
  end_ns=$(python3 - <<'PY'
import time; print(int(time.time()*1_000_000_000))
PY
)
  duration_ms=$(( (end_ns - start_ns) / 1_000_000 ))
  echo "[validate] <<< $name ($status, ${duration_ms}ms) log=$log_file"
  echo "$name|$status|$duration_ms|$log_file" >> "$ARTIFACT_DIR/latest.results"
}

write_summary() {
  if [[ ! -f "$ARTIFACT_DIR/latest.results" ]]; then return; fi
  python3 - "$ARTIFACT_DIR/latest.results" "$ARTIFACT_DIR/latest.json" <<'PY'
import json, sys, pathlib, datetime
rows = []
input_path, out_path = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
for line in input_path.read_text().splitlines():
    name, status, dur, log = line.split("|")
    rows.append({"name": name, "status": status, "duration_ms": int(dur), "log": log})
out = {"generated_at": datetime.datetime.utcnow().isoformat() + "Z", "runs": rows}
out_path.write_text(json.dumps(out, indent=2))
PY
  rm -f "$ARTIFACT_DIR/latest.results"
}

prepare_docs_fixture() {
  local doc_root="$TMP_DIR/docs/modules/ROOT/pages"
  mkdir -p "$doc_root"
  cat > "$doc_root/pipeline-fixture.adoc" <<'EOF'
= Pipeline Fixture

This page exists to keep Antora builds evergreen during local validation.

* Generated: {docdate}
* Purpose: feed validate-pipelines.sh
EOF
}

prepare_pdf_fixture() {
  local pdf="$TMP_DIR/fixture.pdf"
  python3 - <<'PY'
import os
from pathlib import Path
pdf = Path(os.environ["TMP_DIR"]) / "fixture.pdf"
pdf.parent.mkdir(parents=True, exist_ok=True)
content = b"%PDF-1.4\n1 0 obj <<>> endobj\ntrailer <<>>\n%%EOF\n"
pdf.write_bytes(content)
print(pdf)
PY
}

pushd "$ROOT_DIR" >/dev/null

# ensure node pinned
if [[ -f "$ROOT_DIR/scripts/ensure-nvm-node.sh" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT_DIR/scripts/ensure-nvm-node.sh"
fi

# keep tmp tidy (7d)
find "$TMP_DIR" -type f -mtime +7 -delete 2>/dev/null || true

prepare_docs_fixture
PDF_FIXTURE=$(prepare_pdf_fixture)

# pipeline: preflight
if should_run preflight; then
  log_step preflight bash -lc "pnpm run local:preflight"
fi

# pipeline: graph export
if should_run graph; then
  log_step graph bash -lc "scripts/workspace-graph-export.sh"
fi

# pipeline: docs build (uses fixture page automatically discovered by Antora)
if should_run docs; then
  log_step docs bash -lc "pnpm exec antora antora-playbook.ci.yml --stacktrace"
fi

# pipeline: fusion (skip softly if venv missing)
if should_run fusion; then
  if [[ -d "${ROOT_DIR}/n00clear-fusion/.venv" ]]; then
    log_step fusion bash -lc "FUSION_EMBED_BACKEND=${FUSION_EMBED_BACKEND:-stub} .dev/automation/scripts/fusion-pipeline.sh '${PDF_FIXTURE}' validation-fixture"
  else
    echo "[validate] fusion skipped (missing n00clear-fusion/.venv)" | tee "$ARTIFACT_DIR/fusion-skip.log"
  fi
fi

write_summary
popd >/dev/null
echo "[validate] summary -> $ARTIFACT_DIR/latest.json"
