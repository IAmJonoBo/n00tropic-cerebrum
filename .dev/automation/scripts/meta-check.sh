#!/usr/bin/env bash
set -uo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
AUTOMATION_DIR="$ROOT/.dev/automation"
SCRIPTS_DIR="$AUTOMATION_DIR/scripts"
ARTIFACTS_DIR="$AUTOMATION_DIR/artifacts"

AUTO_FIX=${META_CHECK_AUTO_FIX:-0}
DOCTOR=${META_CHECK_DOCTOR:-0}

while [[ $# -gt 0 ]]; do
	case $1 in
	--auto-fix)
		AUTO_FIX=1
		;;
	--doctor)
		DOCTOR=1
		;;
	--help)
		cat <<'USAGE'
Usage: meta-check.sh [--doctor] [--auto-fix]
  --doctor     Run workspace doctor preflight before checks.
  --auto-fix   Attempt safe self-healing actions (implies --doctor).
USAGE
		exit 0
		;;
	*)
		printf '[meta-check] Unknown argument: %s\n' "$1" >&2
		exit 2
		;;
	esac
	shift
done

if [[ $AUTO_FIX -eq 1 ]]; then
	DOCTOR=1
fi

LOG_DIR=${META_CHECK_LOG_DIR:-"$ARTIFACTS_DIR/meta-check"}
LOG_PATH=${META_CHECK_LOG:-"$LOG_DIR/latest.log"}
JSON_PATH=${META_CHECK_JSON:-"$LOG_DIR/latest.json"}
DEPENDENCY_JSON=${META_CHECK_DEPENDENCY_JSON:-"$ARTIFACTS_DIR/dependencies/cross-repo.json"}
RENOVATE_DASHBOARD=${RENOVATE_DASHBOARD:-"$ARTIFACTS_DIR/dependencies/renovate-dashboard.json"}
AGENT_RUN_LOG=${META_CHECK_AGENT_LOG:-"$ARTIFACTS_DIR/automation/agent-runs.json"}
RENOVATE_SECRET_FILE=${RENOVATE_SECRET_FILE:-"$ROOT/.secrets/renovate/config.js"}

mkdir -p "$LOG_DIR"
mkdir -p "$(dirname "$DEPENDENCY_JSON")"
mkdir -p "$(dirname "$AGENT_RUN_LOG")"

: >"$LOG_PATH"
exec > >(tee "$LOG_PATH")
exec 2>&1

STARTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
RESULTS=()
RESULT_FILE=$(mktemp "$LOG_DIR/meta-check-results.XXXXXX")
OVERALL_STATUS=0

log() {
	printf '[meta-check] %s\n' "$1"
}

_sanitize() {
	local value=${1-}
	value=${value//$'\n'/ }
	value=${value//|/\/}
	printf '%s' "$value"
}

record_result() {
	local id="$1"
	local description="$2"
	local status="$3"
	local duration="$4"
	local notes="$5"
	description=$(_sanitize "$description")
	notes=$(_sanitize "$notes")
	RESULTS+=("${id}|${status}|${duration}|${description}|${notes}")
	printf '%s|%s|%s|%s|%s\n' "$id" "$status" "$duration" "$description" "$notes" >>"$RESULT_FILE"
}

run_check() {
	local id="$1"
	local dir="$2"
	local description="$3"
	shift 3
	local start_seconds
	start_seconds=$(date +%s)
	log "→ ${description}"
	if (cd "$ROOT/$dir" && "$@"); then
		local end_seconds
		end_seconds=$(date +%s)
		local duration=$((end_seconds - start_seconds))
		record_result "$id" "$description" "succeeded" "$duration" ""
		log "✅ ${description}"
	else
		local exit_code=$?
		local end_seconds
		end_seconds=$(date +%s)
		local duration=$((end_seconds - start_seconds))
		record_result "$id" "$description" "failed" "$duration" "exit ${exit_code}"
		log "❌ ${description} (exit ${exit_code})"
		OVERALL_STATUS=1
	fi
}

run_command() {
	local id="$1"
	local description="$2"
	shift 2
	local start_seconds
	start_seconds=$(date +%s)
	log "→ ${description}"
	if "$@"; then
		local end_seconds
		end_seconds=$(date +%s)
		local duration=$((end_seconds - start_seconds))
		record_result "$id" "$description" "succeeded" "$duration" ""
		log "✅ ${description}"
	else
		local exit_code=$?
		local end_seconds
		end_seconds=$(date +%s)
		local duration=$((end_seconds - start_seconds))
		record_result "$id" "$description" "failed" "$duration" "exit ${exit_code}"
		log "❌ ${description} (exit ${exit_code})"
		OVERALL_STATUS=1
	fi
}

skip_check() {
	local id="$1"
	local description="$2"
	local reason="$3"
	record_result "$id" "$description" "skipped" "0" "$reason"
	log "⚠️  ${description} skipped: ${reason}"
}

has_command() {
	command -v "$1" >/dev/null 2>&1
}

log "Starting workspace health checks"

if [[ $DOCTOR -eq 1 ]]; then
	if [[ -x "$SCRIPTS_DIR/doctor.sh" ]]; then
		DOCTOR_MODE="check"
		if [[ $AUTO_FIX -eq 1 ]]; then
			DOCTOR_MODE="fix"
		fi
		run_command "doctor" "Workspace doctor (${DOCTOR_MODE})" "$SCRIPTS_DIR/doctor.sh" "--mode=${DOCTOR_MODE}"
	else
		skip_check "doctor" "Workspace doctor" ".dev/automation/scripts/doctor.sh missing"
	fi
fi

if [[ -z ${RENOVATE_TOKEN-} && -f $RENOVATE_SECRET_FILE ]]; then
	# shellcheck disable=SC1090
	source "$RENOVATE_SECRET_FILE"
	export RENOVATE_TOKEN
fi

if [[ -x "$SCRIPTS_DIR/bootstrap-trunk-python.sh" ]]; then
	run_command "bootstrap-trunk" "Bootstrap Trunk Python runtime" "$SCRIPTS_DIR/bootstrap-trunk-python.sh"
fi

if [[ -x "$SCRIPTS_DIR/sync-trunk-configs.sh" ]]; then
	if [[ $AUTO_FIX -eq 1 ]]; then
		run_command "trunk-sync" "Sync Trunk configs (auto-fix)" "$SCRIPTS_DIR/sync-trunk-configs.sh" "--pull"
	else
		run_command "trunk-sync" "Verify Trunk configs" "$SCRIPTS_DIR/sync-trunk-configs.sh" "--check"
	fi
else
	skip_check "trunk-sync" "Verify Trunk configs" "sync-trunk-configs.sh missing"
fi

if has_command python3 && [[ -f "$ROOT/n00-frontiers/tools/export_cortex_assets.py" ]]; then
	run_check "frontiers-export" "n00-frontiers" "n00-frontiers catalog export current" python3 tools/export_cortex_assets.py --check
else
	skip_check "frontiers-export" "n00-frontiers catalog export current" "python3 missing or exporter unavailable"
fi

if [[ -x "$ROOT/n00-frontiers/.dev/sanity-check.sh" ]]; then
	rm -rf "$ROOT/n00-frontiers/.nox" || true
	rm -rf "$ROOT/n00-frontiers/build/template-renders" || true
	run_check "frontiers-sanity" "n00-frontiers" "n00-frontiers sanity" bash -c "TRUNK_SKIP=1 ./.dev/sanity-check.sh --quiet --sections core,templates,examples,dashboards,videos,cloud,tests"
	AUDIT_BIN="$ROOT/.venv-workspace/bin/pip-audit"
	if [[ -x $AUDIT_BIN ]]; then
		run_check "frontiers-pip-audit" "n00-frontiers" "n00-frontiers pip-audit" bash -c "\"$AUDIT_BIN\" -r requirements.txt"
	elif has_command pip-audit; then
		run_check "frontiers-pip-audit" "n00-frontiers" "n00-frontiers pip-audit" bash -c "pip-audit -r requirements.txt"
	else
		skip_check "frontiers-pip-audit" "n00-frontiers pip-audit" "pip-audit not installed"
	fi
else
	skip_check "frontiers-sanity" "n00-frontiers sanity" "sanity script missing"
fi

if has_command python3 && [[ -x "$ROOT/n00-school/scripts/run-training.sh" ]]; then
	SCHOOL_VENV="${ROOT}/n00-school/.venv-meta"
	run_check "school-venv" "n00-school" "Prepare n00-school virtualenv" bash -c "python3 -m venv \"${SCHOOL_VENV}\" >/dev/null 2>&1 || true; source \"${SCHOOL_VENV}/bin/activate\" && python -m pip install -r requirements.txt >/dev/null"
	run_check "school-training-validate" "n00-school" "n00-school pipeline validation" bash -c "source \"${SCHOOL_VENV}/bin/activate\" && scripts/run-training.sh default --check"
	run_check "school-pytest" "n00-school" "n00-school pytest" bash -c "source \"${SCHOOL_VENV}/bin/activate\" && pytest --maxfail=1 --disable-warnings"
else
	skip_check "school-training-validate" "n00-school pipeline validation" "Python runtime or run-training script missing"
fi

if has_command npm && [[ -f "$ROOT/n00-cortex/package.json" ]]; then
	run_check "cortex-schema" "n00-cortex" "n00-cortex schema validation" npm run validate:schemas --silent
	if [[ -x "$SCRIPTS_DIR/ingest-frontiers.sh" ]]; then
		run_check "cortex-frontiers" "." "n00-cortex frontiers ingestion current" "$SCRIPTS_DIR/ingest-frontiers.sh" --check
	else
		run_check "cortex-frontiers" "n00-cortex" "n00-cortex frontiers ingestion current" npm run ingest:frontiers:check --silent
	fi
	if [[ -f "$ROOT/n00-cortex/scripts/generate_docs_manifest.py" ]]; then
		run_check "cortex-docs" "n00-cortex" "n00-cortex docs manifest" bash -c "python3 scripts/generate_docs_manifest.py && npm run validate:docs-manifest --silent"
	else
		skip_check "cortex-docs" "n00-cortex docs manifest" "generate_docs_manifest.py missing"
	fi
else
	skip_check "cortex-schema" "n00-cortex schema validation" "npm missing or package.json not found"
fi

if has_command pnpm && [[ -d "$ROOT/n00t" ]]; then
	if has_command node && node -e "const pkg=require('$ROOT/n00t/package.json'); process.exit(pkg?.scripts?.lint ? 0 : 1)" >/dev/null 2>&1; then
		run_check "n00t-lint" "n00t" "n00t lint" bash -c "pnpm lint"
	else
		skip_check "n00t-lint" "n00t lint" "pnpm lint script missing"
	fi
	if has_command node && node -e "const pkg=require('$ROOT/n00t/package.json'); process.exit(pkg?.scripts?.test ? 0 : 1)" >/dev/null 2>&1; then
		run_check "n00t-test" "n00t" "n00t test" bash -c "pnpm test"
	else
		skip_check "n00t-test" "n00t test" "pnpm test script missing"
	fi
	if has_command node && node -e "const pkg=require('$ROOT/n00t/package.json'); process.exit(pkg?.scripts?.build ? 0 : 1)" >/dev/null 2>&1; then
		run_check "n00t-build" "n00t" "n00t build" bash -c "pnpm build"
	else
		skip_check "n00t-build" "n00t build" "pnpm build script missing"
	fi
else
	skip_check "n00t-lint" "n00t lint" "pnpm missing or repo absent"
	skip_check "n00t-test" "n00t test" "pnpm missing or repo absent"
	skip_check "n00t-build" "n00t build" "pnpm missing or repo absent"
fi

if [[ -d "$ROOT/n00tropic" ]]; then
	if has_command trunk; then
		skip_check "n00tropic-trunk" "n00tropic trunk lint" "meta-check skips trunk lint (set TRUNK_SKIP=0 locally)"
	else
		skip_check "n00tropic-trunk" "n00tropic trunk lint" "trunk CLI not installed"
	fi
fi

if [[ -d "$ROOT/n00plicate" ]]; then
	skip_check "n00plicate-automation" "n00plicate automation" "handled via dedicated pipeline"
fi

if has_command python3 && [[ -x "$SCRIPTS_DIR/validate-project-metadata.py" ]]; then
	PROJECT_METADATA_JSON="$ARTIFACTS_DIR/project-metadata/latest.json"
	mkdir -p "$(dirname "$PROJECT_METADATA_JSON")"
	run_command \
		"project-metadata" \
		"Validate project metadata documents" \
		python3 "$SCRIPTS_DIR/validate-project-metadata.py" \
		--json "$PROJECT_METADATA_JSON"
else
	skip_check "project-metadata" "Validate project metadata documents" "validator script unavailable"
fi

if [[ -x "$SCRIPTS_DIR/check-cross-repo-consistency.py" ]]; then
	run_command "cross-repo" "Cross-repo consistency checks" "$SCRIPTS_DIR/check-cross-repo-consistency.py" --json "$DEPENDENCY_JSON"
else
	skip_check "cross-repo" "Cross-repo consistency checks" "script missing"
fi

if [[ -x "$SCRIPTS_DIR/generate-renovate-dashboard.py" ]]; then
	run_command "renovate-dashboard" "Generate Renovate dependency dashboard" python3 "$SCRIPTS_DIR/generate-renovate-dashboard.py" --output "$RENOVATE_DASHBOARD"
else
	skip_check "renovate-dashboard" "Generate Renovate dependency dashboard" "script missing"
fi

if [[ -x "$SCRIPTS_DIR/check-submodules.sh" ]]; then
	if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
		run_command "submodules" "Submodule hygiene checks" "$SCRIPTS_DIR/check-submodules.sh"
	else
		skip_check "submodules" "Submodule hygiene checks" "workspace root is not a git repository"
	fi
fi

log "Workspace health checks completed"

COMPLETED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
STATUS_LABEL=$([[ $OVERALL_STATUS -eq 0 ]] && echo "succeeded" || echo "failed")

FAILED_DESCRIPTIONS=()
while IFS='|' read -r check_id check_status duration check_desc check_notes; do
	if [[ $check_status == "failed" ]]; then
		FAILED_DESCRIPTIONS+=("$check_desc")
	fi
done <"$RESULT_FILE"

if [[ ${#FAILED_DESCRIPTIONS[@]} -eq 0 ]]; then
	SUMMARY="All checks succeeded"
else
	SUMMARY="Failures: ${FAILED_DESCRIPTIONS[*]}"
fi

python3 - "$JSON_PATH" "$STARTED_AT" "$COMPLETED_AT" "$STATUS_LABEL" "$LOG_PATH" "$SUMMARY" "$ROOT" "$RESULT_FILE" <<'PY'
import json
import sys
from pathlib import Path

json_path = Path(sys.argv[1])
started = sys.argv[2]
completed = sys.argv[3]
status = sys.argv[4]
log_path = sys.argv[5]
summary = sys.argv[6]
root_path = Path(sys.argv[7]).resolve()
results_path = Path(sys.argv[8])

lines = [line.strip() for line in results_path.read_text(encoding="utf-8").splitlines() if line.strip()]
checks = []
for line in lines:
    parts = line.split("|", 4)
    if len(parts) != 5:
        continue
    check_id, check_status, duration, description, notes = parts
    entry = {
        "id": check_id,
        "description": description,
        "status": check_status,
        "durationSeconds": int(duration),
    }
    if notes:
        entry["notes"] = notes
    checks.append(entry)

payload = {
    "generated": completed,
    "started": started,
    "completed": completed,
    "status": status,
    "summary": summary,
    "logPath": str(Path(log_path).resolve().relative_to(root_path)),
    "checks": checks,
}
json_path.parent.mkdir(parents=True, exist_ok=True)
json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(f"[meta-check] Wrote JSON report → {json_path}")
PY

rm -f "$RESULT_FILE"

if [[ -f "$SCRIPTS_DIR/record-capability-run.py" ]]; then
	python3 "$SCRIPTS_DIR/record-capability-run.py" \
		--capability "workspace.metaCheck" \
		--status "$STATUS_LABEL" \
		--summary "$SUMMARY" \
		--log-path "$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$LOG_PATH" "$ROOT")" \
		--started "$STARTED_AT" \
		--completed "$COMPLETED_AT" \
		--metadata "{\"report\": \"$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$JSON_PATH" "$ROOT")\"}"
fi

if [[ -f "$SCRIPTS_DIR/record-run-envelope.py" ]]; then
	python3 "$SCRIPTS_DIR/record-run-envelope.py" \
		--capability "workspace.metaCheck" \
		--status "$STATUS_LABEL" \
		--asset "$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$LOG_PATH" "$ROOT")" \
		--asset "$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$JSON_PATH" "$ROOT")" \
		--notes "$SUMMARY" || true
fi

exit "$OVERALL_STATUS"
