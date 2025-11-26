#!/usr/bin/env bash
# Generate Syft SBOMs for workspace targets.
# AGENT_HOOK: dependency-management
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
MANIFEST_PATH="${ROOT_DIR}/automation/workspace.manifest.json"
export MANIFEST_PATH

usage() {
	cat <<'EOF'
Usage: deps-sbom.sh [--target <name>] [--format cyclonedx-json|spdx-json] [--output-root <path>] [--ref <label>] [--list]

Options:
  --target <name>   Limit to a specific repo name (can repeat). Defaults to all manifest repos.
  --format <fmt>    Syft output format. Defaults to cyclonedx-json.
  --output-root     Directory to write SBOMs (default: artifacts/sbom).
  --ref <label>     Ref/tag label used in output path (default: GITHUB_REF_NAME or git short SHA).
  --list            Print detected targets and exit.
  -h, --help        Show this help text.

The script reads targets from automation/workspace.manifest.json and writes SBOMs to
<output-root>/<target>/<ref>/sbom.<fmt>.json.
EOF
}

require_syft() {
	if command -v syft >/dev/null 2>&1; then
		return 0
	fi
	local fetch_script="${ROOT_DIR}/scripts/fetch-syft.sh"
	if [[ -x ${fetch_script} ]]; then
		echo "[deps-sbom] syft missing; running fetch-syft.sh"
		"${fetch_script}"
	fi
	if ! command -v syft >/dev/null 2>&1; then
		echo "[deps-sbom] syft is required but not found in PATH. Install via https://github.com/anchore/syft#installation." >&2
		exit 1
	fi
}

list_targets() {
	python3 - <<'PY'
import json, sys, os
from pathlib import Path

manifest = Path(os.environ["MANIFEST_PATH"])
data = json.loads(manifest.read_text())
for repo in data.get("repos", []):
    name = repo.get("name")
    path = repo.get("path")
    if name and path:
        print(f"{name}\t{path}")
PY
}

resolve_targets() {
	local filter_json
	filter_json=$(
		python3 - <<'PY'
import json, sys, os
from pathlib import Path

manifest = Path(os.environ["MANIFEST_PATH"])
data = json.loads(manifest.read_text())
requested = os.environ.get("SBOM_TARGETS", "").split(",") if os.environ.get("SBOM_TARGETS") else []
cli_targets = os.environ.get("SBOM_CLI_TARGETS", "").split(",") if os.environ.get("SBOM_CLI_TARGETS") else []
want = [t.strip() for t in (requested + cli_targets) if t.strip()]

repos = {repo.get("name"): repo.get("path") for repo in data.get("repos", []) if repo.get("name") and repo.get("path")}
if want:
    missing = [t for t in want if t not in repos]
    if missing:
        sys.stderr.write(f"Unknown target(s): {', '.join(missing)}\n")
        sys.exit(1)
    selected = {k: repos[k] for k in want}
else:
    selected = repos
print(json.dumps(selected))
PY
	) || return 1
	echo "${filter_json}"
}

main() {
	local format="cyclonedx-json"
	local output_root="${SBOM_OUTPUT_ROOT:-${ROOT_DIR}/artifacts/sbom}"
	local ref_label="${SBOM_REF:-${GITHUB_REF_NAME:-$(git -C "${ROOT_DIR}" rev-parse --short HEAD)}}"
	local list_only=0
	local cli_targets=()

	while [[ $# -gt 0 ]]; do
		case "$1" in
		--target)
			cli_targets+=("$2")
			shift 2
			;;
		--format)
			format="$2"
			shift 2
			;;
		--output-root)
			output_root="$2"
			shift 2
			;;
		--ref)
			ref_label="$2"
			shift 2
			;;
		--list)
			list_only=1
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

	if [[ ${list_only} -eq 1 ]]; then
		list_targets
		exit 0
	fi

	if [[ ${#cli_targets[@]} -gt 0 ]]; then
		export SBOM_CLI_TARGETS="$(
			IFS=,
			echo "${cli_targets[*]}"
		)"
	fi

	require_syft

	local targets_json
	targets_json=$(resolve_targets)
	local syft_version
	syft_version=$(syft version 2>/dev/null | head -n 1 || echo "syft")

	mkdir -p "${output_root}"
	local ext
	case "${format}" in
	cyclonedx-json) ext="cdx.json" ;;
	spdx-json) ext="spdx.json" ;;
	*) ext="${format}.json" ;;
	esac

	ROOT_DIR="${ROOT_DIR}" \
		TARGETS_JSON="${targets_json}" \
		OUTPUT_ROOT="${output_root}" \
		FORMAT="${format}" \
		EXT="${ext}" \
		REF_LABEL="${ref_label}" \
		SYFT_VERSION="${syft_version}" \
		SYFT_LOG="${SYFT_LOG:-error}" \
		SYFT_YARN_ENABLE_EXPERIMENTAL_PARSER="${SYFT_YARN_ENABLE_EXPERIMENTAL_PARSER:-true}" \
		python3 - <<'PY'
import json, os, sys, subprocess, pathlib
from datetime import datetime, timezone

targets = json.loads(os.environ["TARGETS_JSON"])
root = pathlib.Path(os.environ["ROOT_DIR"])
output_root = pathlib.Path(os.environ["OUTPUT_ROOT"])
fmt = os.environ["FORMAT"]
ext = os.environ["EXT"]
ref_label = os.environ["REF_LABEL"]
syft_version = os.environ.get("SYFT_VERSION", "syft")

summary = []
timestamp = datetime.now(timezone.utc).isoformat()

for name, rel_path in targets.items():
    source = root / rel_path
    if not source.exists():
        sys.stderr.write(f"[deps-sbom] Skipping {name}: path missing ({source})\n")
        continue
    out_dir = output_root / name / ref_label
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"sbom.{ext}"
    cmd = [
        "syft",
        "scan",
        f"dir:{source}",
        "-o",
        f"{fmt}={out_file}",
    ]
    env = os.environ.copy()
    env.setdefault(
        "SYFT_EXCLUDE",
        "./.git,./node_modules,./.venv,./build,./dist,./.mypy_cache,./.pytest_cache",
    )
    env.setdefault("SYFT_LOG", "error")
    print(f"[deps-sbom] Generating SBOM for {name} -> {out_file}")
    subprocess.run(cmd, check=True, env=env)
    meta = {
        "target": name,
        "path": str(source),
        "ref": ref_label,
        "format": fmt,
        "output": str(out_file),
        "generated_at": timestamp,
        "syft": syft_version,
    }
    meta_path = out_dir / "run.json"
    meta_path.write_text(json.dumps(meta, indent=2))
    summary.append(meta)

index_path = output_root / "latest.json"
index_path.write_text(json.dumps(summary, indent=2))
print(f"[deps-sbom] Wrote index -> {index_path}")
PY
	echo "[deps-sbom] status=ok"
}
main "$@"
