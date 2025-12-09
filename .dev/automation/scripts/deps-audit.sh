#!/usr/bin/env bash
# Generate SBOMs then upload to Dependency-Track.
# AGENT_HOOK: dependency-management
set -euo pipefail
IFS=$'\n\t'

# shellcheck source=./lib/log.sh
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib/log.sh"
# shellcheck source=../toolchain.env
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")"/.. && pwd)/toolchain.env"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
MANIFEST_PATH="${ROOT_DIR}/automation/workspace.manifest.json"
export MANIFEST_PATH

usage() {
	cat <<'EOF'
Usage: deps-audit.sh [--target <name>] [--ref <label>] [--format cyclonedx-json|spdx-json] [--skip-upload]

Runs deps-sbom followed by Dependency-Track upload for the selected targets.
Env: DEPENDENCY_TRACK_BASE_URL, DEPENDENCY_TRACK_API_KEY for uploads.
EOF
}

list_manifest_targets() {
	python3 - <<'PY'
import json, os
from pathlib import Path

manifest = Path(os.environ["MANIFEST_PATH"])
data = json.loads(manifest.read_text())
names = [repo.get("name") for repo in data.get("repos", []) if repo.get("name")]
print(" ".join(names))
PY
}

main() {
	local targets=()
	local ref_label="${SBOM_REF:-${GITHUB_REF_NAME:-$(git -C "${ROOT_DIR}" rev-parse --short HEAD)}}"
	local format="cyclonedx-json"
	local skip_upload=0

	while [[ $# -gt 0 ]]; do
		case "$1" in
		--target)
			targets+=("$2")
			shift 2
			;;
		--ref)
			ref_label="$2"
			shift 2
			;;
		--format)
			format="$2"
			shift 2
			;;
		--skip-upload)
			skip_upload=1
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

	local target_env=""
	if [[ ${#targets[@]} -gt 0 ]]; then
		target_env=$(
			IFS=,
			echo "${targets[*]}"
		)
	fi

	SBOM_TARGETS="${target_env}" SBOM_REF="${ref_label}" SBOM_OUTPUT_ROOT="${SBOM_OUTPUT_ROOT:-${ROOT_DIR}/artifacts/sbom}" "${SCRIPT_DIR}/deps-sbom.sh" --format "${format}" ${targets[@]/#/--target }

	if [[ ${skip_upload} -eq 1 ]]; then
		exit 0
	fi

	# Determine targets to upload
	local upload_targets=()
	if [[ ${#targets[@]} -gt 0 ]]; then
		upload_targets=(${targets[@]})
	else
		read -r -a upload_targets <<<"$(list_manifest_targets)"
	fi

	for target in "${upload_targets[@]}"; do
		DEPENDENCY_TRACK_BASE_URL="${DEPENDENCY_TRACK_BASE_URL-}" \
			DEPENDENCY_TRACK_API_KEY="${DEPENDENCY_TRACK_API_KEY-}" \
			SBOM_REF="${ref_label}" \
			"${SCRIPT_DIR}/deps-dependency-track-upload.sh" --target "${target}"
	done

	echo "[deps-audit] status=ok"
}

main "$@"
