#!/usr/bin/env bash
# Upload generated SBOMs to OWASP Dependency-Track.
# AGENT_HOOK: dependency-management
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
PROJECTS_FILE="${ROOT_DIR}/ops/dependency-track/projects.json"

usage() {
	cat <<'EOF'
Usage: deps-dependency-track-upload.sh --target <name> [--sbom <path>] [--ref <label>] [--dry-run]

Env vars:
  DEPENDENCY_TRACK_BASE_URL   Base URL of the Dependency-Track instance (e.g., https://dtrack.example.com)
  DEPENDENCY_TRACK_API_KEY    API key with BOM upload permission

Options:
  --target <name>  Target repo name matching automation/workspace.manifest.json
  --sbom <path>    Path to SBOM file (defaults to artifacts/sbom/<target>/<ref>/sbom.cdx.json)
  --ref <label>    Project version label (defaults to GITHUB_REF_NAME or git short SHA)
  --dry-run        Print request info without uploading
  -h, --help       Show this help text
EOF
}

require_env() {
	# Accept DT_BASE_URL as an alias for DEPENDENCY_TRACK_BASE_URL
	if [[ -z ${DEPENDENCY_TRACK_BASE_URL-} && -n ${DT_BASE_URL-} ]]; then
		DEPENDENCY_TRACK_BASE_URL="${DT_BASE_URL}"
	fi
	if [[ -z ${DEPENDENCY_TRACK_API_KEY-} ]]; then
		if [[ -n ${DT_API_KEY-} ]]; then
			DEPENDENCY_TRACK_API_KEY="${DT_API_KEY}"
		fi
	fi
	if [[ -z ${DEPENDENCY_TRACK_BASE_URL-} || -z ${DEPENDENCY_TRACK_API_KEY-} ]]; then
		echo "[deps-dtrack] WARNING: missing DEPENDENCY_TRACK_BASE_URL (or DT_BASE_URL) or DEPENDENCY_TRACK_API_KEY; skipping upload." >&2
		return 1
	fi
}

resolve_project_name() {
	local target="${TARGET_NAME-}"
	python3 - <<'PY'
import json, os, sys
from pathlib import Path

target = os.environ["TARGET_NAME"]
projects_path = Path(os.environ["PROJECTS_FILE"])
default_name = f"n00tropic-cerebrum::{target}"
if not projects_path.exists():
    print(default_name)
    sys.exit(0)

data = json.loads(projects_path.read_text())
for comp in data.get("components", []):
    if comp.get("name") == target:
        print(comp.get("projectName") or default_name)
        sys.exit(0)
print(default_name)
PY
}

encode_bom() {
	python3 - <<'PY'
import base64, json, os, sys
from pathlib import Path

bom_path = Path(os.environ["SBOM_PATH"])
payload = {
    "projectName": os.environ["PROJECT_NAME"],
    "projectVersion": os.environ["PROJECT_VERSION"],
    "autoCreate": True,
    "bom": base64.b64encode(bom_path.read_bytes()).decode(),
}
print(json.dumps(payload))
PY
}

main() {
	local target=""
	local ref_label="${SBOM_REF:-${GITHUB_REF_NAME:-$(git -C "${ROOT_DIR}" rev-parse --short HEAD)}}"
	local sbom_path=""
	local dry_run=0

	while [[ $# -gt 0 ]]; do
		case "$1" in
		--target)
			target="$2"
			shift 2
			;;
		--sbom)
			sbom_path="$2"
			shift 2
			;;
		--ref)
			ref_label="$2"
			shift 2
			;;
		--dry-run)
			dry_run=1
			shift
			;;
		-h | --help)
			usage
			exit 0
			;;
		*)
			echo "Unknown option: $1" >&2
			usage
			exit 1
			;;
		esac
	done

	if [[ -z ${target} ]]; then
		echo "[deps-dtrack] --target is required" >&2
		usage
		exit 1
	fi

	if [[ -z ${sbom_path} ]]; then
		sbom_path="${ROOT_DIR}/artifacts/sbom/${target}/${ref_label}/sbom.cdx.json"
	fi

	if [[ ! -f ${sbom_path} ]]; then
		echo "[deps-dtrack] SBOM not found at ${sbom_path}" >&2
		exit 1
	fi

	PROJECT_NAME=$(TARGET_NAME="${target}" PROJECTS_FILE="${PROJECTS_FILE}" resolve_project_name)
	PROJECT_VERSION="${ref_label}"
	out_dir="${ROOT_DIR}/artifacts/sbom/${target}/${ref_label}"
	mkdir -p "${out_dir}"
	export SBOM_PATH="${sbom_path}"
	export PROJECT_NAME PROJECT_VERSION

	if [[ ${dry_run} -eq 1 ]]; then
		cat <<EOF
[deps-dtrack] dry-run
  project: ${PROJECT_NAME}
  version: ${PROJECT_VERSION}
  sbom:    ${sbom_path}
EOF
		exit 0
	fi

	if ! require_env; then
		echo "[deps-dtrack] status=skipped"
		return 0
	fi

	# Prepare base64 payload for multipart upload (avoids long cmdlines and 415s)
	echo "[deps-dtrack] Uploading BOM for ${PROJECT_NAME} (${PROJECT_VERSION})"
	response=$(curl -sSf -X POST "${DEPENDENCY_TRACK_BASE_URL%/}/api/v1/bom" \
		-H "X-Api-Key: ${DEPENDENCY_TRACK_API_KEY}" \
		-F "projectName=${PROJECT_NAME}" \
		-F "projectVersion=${PROJECT_VERSION}" \
		-F "autoCreate=true" \
		-F "bom=@${sbom_path};type=application/json")

	out_dir="${ROOT_DIR}/artifacts/sbom/${target}/${ref_label}"
	mkdir -p "${out_dir}"
	echo "${response}" >"${out_dir}/dependency-track-response.json"
	echo "[deps-dtrack] Response stored at ${out_dir}/dependency-track-response.json"
	echo "[deps-dtrack] status=ok"
}

main "$@"
