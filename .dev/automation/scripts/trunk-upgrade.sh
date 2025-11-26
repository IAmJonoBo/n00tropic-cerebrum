#!/usr/bin/env bash
set -uo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
SCRIPTS_DIR="$ROOT/.dev/automation/scripts"
DEFAULT_CMD_TIMEOUT="${TRUNK_CMD_TIMEOUT:-300}"
TRUNK_INSTALL_ALLOWED="${TRUNK_INSTALL:-${CI:-0}}"
TRUNK_INIT_MISSING="${TRUNK_INIT_MISSING:-1}"

log() {
	printf '[trunk-upgrade] %s\n' "$1"
}

usage() {
	cat <<'USAGE'
Usage: trunk-upgrade.sh [--repo <name>]...

Runs `trunk upgrade --no-progress` in every repository that contains a `.trunk/trunk.yaml`
file. When one or more `--repo` flags are supplied, limits execution to those repositories.
If `TRUNK_INIT_MISSING=1` (default), repositories without `.trunk/trunk.yaml` are
auto-initialized with `trunk init --ci --yes --no-progress` to enable recommended linters
per repo before upgrading.

Environment variables:
  TRUNK_UPGRADE_FLAGS   Extra flags to pass to `trunk upgrade` (space-delimited).
  TRUNK_INSTALL         Set to 1 (or CI=1) to permit automatic CLI install when missing.
  TRUNK_INSTALL_SKIP    Set to `1` to skip the automatic installation attempt when the
                        Trunk CLI is missing.
  TRUNK_INIT_MISSING    Default 1. When set to 1, run `trunk init --ci --yes` in repos
                        that lack `.trunk/trunk.yaml` (per-repo recommended linters).
USAGE
}

ensure_trunk() {
	export PATH="$HOME/.trunk/bin:$PATH"
	if command -v trunk >/dev/null 2>&1; then
		return 0
	fi

	if [[ ${TRUNK_INSTALL_ALLOWED} != "1" ]]; then
		log "Trunk CLI not found. Set TRUNK_INSTALL=1 (or CI=1) to allow a one-time install, or run 'trunk upgrade --no-progress' manually."
		return 1
	fi

	if [[ ${TRUNK_INSTALL_SKIP:-0} == "1" ]]; then
		log "Trunk CLI not found and TRUNK_INSTALL_SKIP=1; aborting."
		return 1
	fi

	if ! command -v curl >/dev/null 2>&1; then
		log "Trunk CLI not found and curl is unavailable; cannot install automatically."
		return 1
	fi

	log "Installing Trunk CLI (not detected in PATH)."
	local installer
	installer=$(mktemp)
	if ! curl -fsSL https://get.trunk.io -o "$installer"; then
		log "Failed to download Trunk installer script."
		rm -f "$installer"
		return 1
	fi

	if ! bash "$installer" -y >/dev/null 2>&1; then
		log "Primary installer invocation failed; retrying without -y flag."
		if ! bash "$installer" >/dev/null 2>&1; then
			log "Trunk installer execution failed."
			rm -f "$installer"
			return 1
		fi
	fi

	rm -f "$installer"

	if command -v trunk >/dev/null 2>&1; then
		log "Trunk CLI installed successfully."
		return 0
	fi

	log "Trunk CLI still unavailable after installation attempt."
	return 1
}

discover_repos() {
	find "$ROOT" -maxdepth 3 -type f -path "*/.trunk/trunk.yaml" -print | while read -r trunk_file; do
		local repo
		repo=$(basename "$(dirname "$(dirname "$trunk_file")")")
		printf '%s\n' "$repo"
	done | sort -u
}

contains_repo() {
	local needle="$1"
	shift || true
	for candidate in "$@"; do
		if [[ $candidate == "$needle" ]]; then
			return 0
		fi
	done
	return 1
}

missing_from_manifest() {
	local manifest="$ROOT/automation/workspace.manifest.json"
	[[ -f $manifest ]] || return 0
	python3 - <<'PY'
import json, os, sys
from pathlib import Path

root = Path(os.environ["ROOT"])
manifest = root / "automation" / "workspace.manifest.json"
data = json.loads(manifest.read_text())
existing = set()
for p in sys.argv[1:]:
    existing.add(p)

paths = []
for repo in data.get("repos", []):
    path = repo.get("path")
    name = repo.get("name")
    if not path or not name:
        continue
    repo_path = root / path
    if (repo_path / ".trunk" / "trunk.yaml").exists():
        continue
    paths.append((name, str(repo_path)))

for name, path in paths:
    print(f"{name}\t{path}")
PY
}

ensure_trunk_init() {
	local repo_name="$1"
	local repo_path="$2"
	if [[ ! -d $repo_path ]]; then
		log "Skipping init for $repo_name (missing path $repo_path)"
		return 1
	fi
	log "Initializing Trunk in $repo_name"
	if (
		cd "$repo_path" &&
			TRUNK_NO_PROGRESS=1 TRUNK_DISABLE_TELEMETRY=1 TRUNK_NONINTERACTIVE=1 trunk init --ci --no-progress
	); then
		return 0
	else
		log "⚠️  trunk init failed in $repo_name"
		return 1
	fi
}

run_with_timeout() {
	local timeout="$1"
	shift
	if [[ $timeout -le 0 ]]; then
		"$@"
		return $?
	fi
	if command -v gtimeout >/dev/null 2>&1; then
		gtimeout "$timeout" "$@"
		return $?
	elif command -v timeout >/dev/null 2>&1; then
		timeout "$timeout" "$@"
		return $?
	fi

	python3 - "$timeout" "$@" <<'PY'
import shlex
import subprocess
import sys

timeout = float(sys.argv[1])
cmd = sys.argv[2:]
try:
    proc = subprocess.run(cmd, check=False, timeout=timeout)
    sys.exit(proc.returncode)
except subprocess.TimeoutExpired:
    printable = " ".join(shlex.quote(part) for part in cmd)
    print(f"[trunk-upgrade] command {printable} timed out after {timeout:.0f}s", file=sys.stderr)
    sys.exit(124)
PY
}

STARTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

REQUESTED=()
if [[ -n ${TRUNK_UPGRADE_REPOS-} ]]; then
	while IFS= read -r repo; do
		[[ -n $repo ]] && REQUESTED+=("$repo")
	done < <(
		python3 - <<'PY'
import json
import os
import sys

raw = os.environ.get("TRUNK_UPGRADE_REPOS", "").strip()
if not raw:
    sys.exit(0)

def emit(items):
    for item in items:
        if isinstance(item, str) and item.strip():
            print(item.strip())

try:
    parsed = json.loads(raw)
except json.JSONDecodeError:
    parsed = None

if isinstance(parsed, str):
    emit([parsed])
elif isinstance(parsed, (list, tuple)):
    emit(parsed)
else:
    parts = raw.replace(",", " ").split()
    emit(parts)
PY
	)
fi
while [[ $# -gt 0 ]]; do
	case "$1" in
	--repo)
		if [[ $# -lt 2 ]]; then
			log "--repo expects a repository name"
			usage
			exit 2
		fi
		REQUESTED+=("$2")
		shift 2
		;;
	--help)
		usage
		exit 0
		;;
	*)
		log "Unknown argument: $1"
		usage
		exit 2
		;;
	esac
done

ALL_REPOS=()
while IFS= read -r repo; do
	[[ -n $repo ]] && ALL_REPOS+=("$repo")
done < <(discover_repos)

if [[ $TRUNK_INIT_MISSING == "1" ]]; then
	MISSING_INIT=()
	while IFS=$'\t' read -r name path; do
		[[ -z $name ]] && continue
		MISSING_INIT+=("$name::$path")
	done < <(ROOT="$ROOT" missing_from_manifest)
	for entry in "${MISSING_INIT[@]}"; do
		repo_name="${entry%%::*}"
		repo_path="${entry##*::}"
		if ensure_trunk_init "$repo_name" "$repo_path"; then
			ALL_REPOS+=("$repo_name")
		fi
	done
fi

if [[ ${#ALL_REPOS[@]} -eq 0 ]]; then
	log "No repositories with .trunk/trunk.yaml discovered."
	exit 0
fi

TARGET_REPOS=()
if [[ ${#REQUESTED[@]} -eq 0 ]]; then
	TARGET_REPOS=("${ALL_REPOS[@]}")
else
	for repo in "${REQUESTED[@]}"; do
		if contains_repo "$repo" "${ALL_REPOS[@]}"; then
			TARGET_REPOS+=("$repo")
		else
			log "Requested repo '$repo' not found or lacks .trunk/trunk.yaml."
		fi
	done
fi

if [[ ${#TARGET_REPOS[@]} -eq 0 ]]; then
	log "No matching repositories to process."
	exit 1
fi

if ! ensure_trunk; then
	STATUS="failed"
	SUMMARY="Trunk CLI unavailable"
	COMPLETED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
	if [[ -f "$SCRIPTS_DIR/record-capability-run.py" ]]; then
		python3 "$SCRIPTS_DIR/record-capability-run.py" \
			--capability "workspace.trunkUpgrade" \
			--status "$STATUS" \
			--summary "$SUMMARY" \
			--started "$STARTED_AT" \
			--completed "$COMPLETED_AT"
	fi
	exit 1
fi

log "Discovered repositories: ${TARGET_REPOS[*]}"

EXTRA_FLAGS=()
if [[ -n ${TRUNK_UPGRADE_FLAGS-} ]]; then
	while IFS= read -r flag; do
		[[ -n $flag ]] && EXTRA_FLAGS+=("$flag")
	done < <(
		python3 - <<'PY'
import json
import os
import sys

raw = os.environ.get("TRUNK_UPGRADE_FLAGS", "").strip()
if not raw:
  sys.exit(0)

def emit(items):
  for item in items:
    if isinstance(item, str) and item.strip():
      print(item.strip())

try:
  parsed = json.loads(raw)
except json.JSONDecodeError:
  parsed = None

if isinstance(parsed, str):
  emit([parsed])
elif isinstance(parsed, (list, tuple)):
  emit(parsed)
else:
  emit(raw.replace(",", " ").split())
PY
	)
fi

SUCCEEDED=()
FAILED=()

for repo in "${TARGET_REPOS[@]}"; do
	local_path="$ROOT/$repo"
	if [[ ! -d $local_path ]]; then
		log "Skipping $repo (directory missing)"
		FAILED+=("$repo")
		continue
	fi

	log "Upgrading Trunk plugins in $repo"
	if (
		cd "$local_path" &&
			run_with_timeout "$DEFAULT_CMD_TIMEOUT" env TRUNK_NO_PROGRESS=1 TRUNK_DISABLE_TELEMETRY=1 \
				trunk upgrade --no-progress ${EXTRA_FLAGS[@]+"${EXTRA_FLAGS[@]}"}
	); then
		SUCCEEDED+=("$repo")
	else
		exit_code=$?
		log "⚠️  trunk upgrade failed in $repo (exit ${exit_code})"
		FAILED+=("$repo")
	fi
done

COMPLETED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [[ ${#FAILED[@]} -eq 0 ]]; then
	STATUS="succeeded"
	SUMMARY="Trunk upgraded in ${#SUCCEEDED[@]} repositories"
	log "✅ Trunk upgrades completed successfully"
else
	STATUS="failed"
	SUMMARY="Failures in ${FAILED[*]}"
	log "⚠️  Trunk upgrades completed with issues"
fi

if [[ -f "$SCRIPTS_DIR/record-capability-run.py" ]]; then
	python3 "$SCRIPTS_DIR/record-capability-run.py" \
		--capability "workspace.trunkUpgrade" \
		--status "$STATUS" \
		--summary "$SUMMARY" \
		--started "$STARTED_AT" \
		--completed "$COMPLETED_AT"
fi

if [[ ${#FAILED[@]} -ne 0 ]]; then
	exit 1
fi

exit 0
