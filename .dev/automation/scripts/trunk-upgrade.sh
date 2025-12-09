#!/usr/bin/env bash
set -uo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
ROOT_NAME=$(basename "$ROOT")
SCRIPTS_DIR="$ROOT/.dev/automation/scripts"
STATE_FILE="$ROOT/.dev/automation/artifacts/automation/trunk-upgrade-state.json"
STATE_DIR=$(dirname "$STATE_FILE")
mkdir -p "$STATE_DIR"
DEFAULT_CMD_TIMEOUT="${TRUNK_CMD_TIMEOUT:-300}"
TRUNK_INSTALL_ALLOWED="${TRUNK_INSTALL:-${CI:-0}}"
TRUNK_INIT_MISSING="${TRUNK_INIT_MISSING:-1}"
export TRUNK_CACHE_ROOT="${TRUNK_CACHE_ROOT:-$ROOT/.cache/trunk}"

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

CURRENT_HASHES=$(
	python3 - "$ROOT" "$ROOT_NAME" "${ALL_REPOS[@]}" <<'PY'
import hashlib
import json
import os
import sys

root = sys.argv[1]
root_name = sys.argv[2]
repos = sys.argv[3:]
hashes = {}
for repo in repos:
	if repo == root_name:
		trunk_file = os.path.join(root, ".trunk", "trunk.yaml")
	else:
		trunk_file = os.path.join(root, repo, ".trunk", "trunk.yaml")
	if os.path.isfile(trunk_file):
		with open(trunk_file, "rb") as handle:
			hashes[repo] = hashlib.sha256(handle.read()).hexdigest()
	else:
		hashes[repo] = "missing"
print(json.dumps(hashes))
PY
)
export TRUNK_UPGRADE_CURRENT_HASHES="$CURRENT_HASHES"

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

SMART_MODE="${TRUNK_UPGRADE_SMART:-0}"
FORCE_ALL="${TRUNK_UPGRADE_FORCE_ALL:-0}"
if [[ ${#REQUESTED[@]} -eq 0 && ${#TARGET_REPOS[@]} -gt 0 && $SMART_MODE == "1" && $FORCE_ALL != "1" ]]; then
	mapfile -t SMART_INFO < <(
		python3 - "$STATE_FILE" <<'PY'
import json
import os
import sys

state_file = sys.argv[1]
current = json.loads(os.environ.get("TRUNK_UPGRADE_CURRENT_HASHES", "{}"))
previous = {}
last_updated = ""
if os.path.isfile(state_file):
    try:
        with open(state_file, "r", encoding="utf-8") as existing:
            state = json.load(existing)
            previous = state.get("hashes", {})
            last_updated = state.get("updated") or ""
    except Exception:
        previous = {}

changed = [repo for repo, digest in current.items() if previous.get(repo) != digest]
print(json.dumps(changed))
print(last_updated)
PY
	)
	SMART_JSON="${SMART_INFO[0]:-[]}"
	LAST_UPDATED="${SMART_INFO[1]-}"
	if [[ -n $SMART_JSON ]]; then
		mapfile -t SMART_REPOS < <(
			python3 - "$SMART_JSON" <<'PY'
import json
import sys

data = json.loads(sys.argv[1])
for item in data:
    print(item)
PY
		)
		if [[ ${#SMART_REPOS[@]} -gt 0 ]]; then
			log "Smart mode limiting Trunk upgrades to: ${SMART_REPOS[*]}"
			TARGET_REPOS=("${SMART_REPOS[@]}")
		else
			MAX_AGE="${TRUNK_UPGRADE_MAX_AGE:-86400}"
			AGE_SECONDS=""
			if [[ -n $LAST_UPDATED ]]; then
				AGE_SECONDS=$(
					python3 - "$LAST_UPDATED" <<'PY'
from datetime import datetime, timezone
import sys

stamp = sys.argv[1]
try:
    dt = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    age = int((datetime.now(timezone.utc) - dt).total_seconds())
    print(age)
except Exception:
    print("")
PY
				)
			fi
			if [[ -n $AGE_SECONDS && $AGE_SECONDS -lt $MAX_AGE ]]; then
				log "Smart mode detected no repo drift in the last ${AGE_SECONDS}s (threshold ${MAX_AGE}s); skipping Trunk upgrade."
				exit 0
			else
				log "Smart mode TTL exceeded or no prior run recorded; running full upgrade"
			fi
		fi
	fi
fi

if [[ -n ${TRUNK_UPGRADE_ALWAYS_INCLUDE-} ]]; then
	mapfile -t ALWAYS_INCLUDE < <(
		python3 - "${TRUNK_UPGRADE_ALWAYS_INCLUDE}" <<'PY'
import json
import os
import sys

raw = sys.argv[1]
try:
    parsed = json.loads(raw)
    if isinstance(parsed, str):
        parsed = [parsed]
    elif not isinstance(parsed, (list, tuple)):
        parsed = str(raw).replace(",", " ").split()
except json.JSONDecodeError:
    parsed = str(raw).replace(",", " ").split()

for item in parsed:
    value = str(item).strip()
    if value:
        print(value)
PY
	)
	for extra in "${ALWAYS_INCLUDE[@]}"; do
		contains_repo "$extra" "${TARGET_REPOS[@]}" || TARGET_REPOS+=("$extra")
	done
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

upgrade_repo() {
	local repo="$1"
	local local_path="$ROOT/$repo"
	[[ $repo == "$ROOT_NAME" ]] && local_path="$ROOT"
	if [[ ! -d $local_path ]]; then
		log "Skipping $repo (directory missing)"
		return 2
	fi

	log "Upgrading Trunk plugins in $repo"
	if (
		cd "$local_path" &&
			run_with_timeout "$DEFAULT_CMD_TIMEOUT" env TRUNK_NO_PROGRESS=1 TRUNK_DISABLE_TELEMETRY=1 \
				trunk upgrade --no-progress ${EXTRA_FLAGS[@]+"${EXTRA_FLAGS[@]}"}
	); then
		return 0
	else
		exit_code=$?
		log "⚠️  trunk upgrade failed in $repo (exit ${exit_code})"
		return "$exit_code"
	fi
}

SUCCEEDED=()
FAILED=()

PARALLEL_JOBS="${TRUNK_UPGRADE_JOBS:-1}"
if ! [[ $PARALLEL_JOBS =~ ^[0-9]+$ ]]; then
	PARALLEL_JOBS=1
fi
if [[ $PARALLEL_JOBS -lt 1 ]]; then
	PARALLEL_JOBS=1
fi

if [[ $PARALLEL_JOBS -le 1 || ${#TARGET_REPOS[@]} -le 1 ]]; then
	for repo in "${TARGET_REPOS[@]}"; do
		if upgrade_repo "$repo"; then
			SUCCEEDED+=("$repo")
		else
			FAILED+=("$repo")
		fi
	done
else
	log "Running Trunk upgrades with up to $PARALLEL_JOBS concurrent jobs"
	TMP_LOG_DIR=$(mktemp -d -t trunk-upgrade-XXXXXX)
	cleanup_logs() {
		if [[ -n ${TMP_LOG_DIR-} && -d $TMP_LOG_DIR ]]; then
			rm -rf "$TMP_LOG_DIR"
		fi
	}
	trap cleanup_logs EXIT
	declare -A PID_TO_REPO=()
	declare -A PID_TO_LOG=()
	ACTIVE_PIDS=()

	start_job() {
		local repo="$1"
		local log_file="$TMP_LOG_DIR/${repo//[^A-Za-z0-9_.-]/_}.log"
		(
			upgrade_repo "$repo"
		) >"$log_file" 2>&1 &
		local pid=$!
		PID_TO_REPO[$pid]="$repo"
		PID_TO_LOG[$pid]="$log_file"
		ACTIVE_PIDS+=("$pid")
	}

	wait_for_pid() {
		local pid="$1"
		local repo="${PID_TO_REPO[$pid]}"
		local log_file="${PID_TO_LOG[$pid]}"
		if wait "$pid"; then
			SUCCEEDED+=("$repo")
		else
			FAILED+=("$repo")
		fi
		if [[ -f $log_file ]]; then
			cat "$log_file"
			rm -f "$log_file"
		fi
		unset PID_TO_REPO[$pid]
		unset PID_TO_LOG[$pid]
	}

	for repo in "${TARGET_REPOS[@]}"; do
		start_job "$repo"
		while [[ ${#ACTIVE_PIDS[@]} -ge $PARALLEL_JOBS ]]; do
			pid="${ACTIVE_PIDS[0]}"
			wait_for_pid "$pid"
			ACTIVE_PIDS=(${ACTIVE_PIDS[@]:1})
		done
	done

	while [[ ${#ACTIVE_PIDS[@]} -gt 0 ]]; do
		pid="${ACTIVE_PIDS[0]}"
		wait_for_pid "$pid"
		ACTIVE_PIDS=(${ACTIVE_PIDS[@]:1})
	done

	trap - EXIT
	cleanup_logs
fi

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

POST_RUN_HASHES=$(
	python3 - "$ROOT" "$ROOT_NAME" "${ALL_REPOS[@]}" <<'PY'
import hashlib
import json
import os
import sys

root = sys.argv[1]
root_name = sys.argv[2]
repos = sys.argv[3:]
hashes = {}
for repo in repos:
    if repo == root_name:
        trunk_file = os.path.join(root, ".trunk", "trunk.yaml")
    else:
        trunk_file = os.path.join(root, repo, ".trunk", "trunk.yaml")
    if os.path.isfile(trunk_file):
        with open(trunk_file, "rb") as handle:
            hashes[repo] = hashlib.sha256(handle.read()).hexdigest()
    else:
        hashes[repo] = "missing"
print(json.dumps(hashes))
PY
)
export TRUNK_UPGRADE_POST_HASHES="$POST_RUN_HASHES"

if [[ -n ${TRUNK_UPGRADE_CURRENT_HASHES-} ]]; then
	SUCCEEDED_CSV=$(
		IFS=,
		echo "${SUCCEEDED[*]}"
	)
	FAILED_CSV=$(
		IFS=,
		echo "${FAILED[*]}"
	)
	python3 - "$STATE_FILE" "$SUCCEEDED_CSV" "$FAILED_CSV" <<'PY'
import json
import os
import sys
import time

state_path = sys.argv[1]
succeeded = {entry for entry in sys.argv[2].split(",") if entry}
failed = {entry for entry in sys.argv[3].split(",") if entry}

payload = os.environ.get("TRUNK_UPGRADE_POST_HASHES") or os.environ.get("TRUNK_UPGRADE_CURRENT_HASHES", "{}")
try:
	current = json.loads(payload)
except json.JSONDecodeError:
	current = {}

try:
    with open(state_path, "r", encoding="utf-8") as existing:
        state = json.load(existing)
except Exception:
    state = {}

hashes = state.get("hashes", {})
for repo, digest in current.items():
    if repo in failed:
        continue
    hashes[repo] = digest

state["hashes"] = hashes
state["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

with open(state_path, "w", encoding="utf-8") as handle:
    json.dump(state, handle, indent=2)
PY
fi

if [[ ${TRUNK_POST_SYNC:-1} == "1" ]]; then
	log "Running post-upgrade trunk config sync (auto-promote enabled)"
	if ! "$SCRIPTS_DIR/sync-trunk-configs.sh" --check; then
		log "Post-upgrade trunk sync reported changes or drift"
	fi
fi

if [[ ${#FAILED[@]} -ne 0 ]]; then
	exit 1
fi

exit 0
