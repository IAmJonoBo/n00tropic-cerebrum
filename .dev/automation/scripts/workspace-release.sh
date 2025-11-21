#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
SCRIPTS_DIR="$ROOT/.dev/automation/scripts"
DOCS_DIR="$ROOT/1. Cerebrum Docs"
MANIFEST="$DOCS_DIR/releases.yaml"
STARTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SUMMARY="Release manifest generated"

log() {
	printf '[workspace-release] %s\n' "$1"
}

finalise_run() {
	local exit_code=$?
	local status="succeeded"
	if [[ $exit_code -ne 0 ]]; then
		status="failed"
	fi
	local completed
	completed=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
	if [[ -f "$SCRIPTS_DIR/record-capability-run.py" ]]; then
		python3 "$SCRIPTS_DIR/record-capability-run.py" \
			--capability "workspace.release" \
			--status "$status" \
			--summary "$SUMMARY" \
			--started "$STARTED_AT" \
			--completed "$completed" \
			--metadata "{\"manifest\": \"$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' \""$MANIFEST"\" \""$ROOT"\")\"}"
	fi
	return "$exit_code"
}

trap 'finalise_run' EXIT

log "Ensuring canonical Trunk configuration"
if ! "$SCRIPTS_DIR/sync-trunk-configs.sh" --check; then
	log "❌ Trunk configuration drift detected. Run '.dev/automation/scripts/sync-trunk-configs.sh --write' and commit the changes before releasing."
	exit 2
fi

require_clean_tree() {
	local dir="$1"
	(cd "$ROOT/$dir" && git diff --quiet --stat && git diff --cached --quiet) || {
		log "❌ Repository $dir has uncommitted changes. Aborting."
		exit 2
	}
}

get_latest_tag() {
	local dir="$1"
	(cd "$ROOT/$dir" && git describe --tags --abbrev=0 2>/dev/null || echo "unreleased")
}

write_manifest_entry() {
	local repo="$1"
	local tag="$2"
	printf '  - repo: %s\n    tag: %s\n' "$repo" "$tag"
}

log "Verifying cleanliness"
require_clean_tree "n00-frontiers"
require_clean_tree "n00-cortex"
require_clean_tree "n00t"
require_clean_tree "n00tropic"
require_clean_tree "n00plicate"

log "Running cross-repo consistency check"
"$SCRIPTS_DIR/check-cross-repo-consistency.py" --json "$ROOT/.dev/automation/artifacts/dependencies/cross-repo.json"

log "Collecting release tags"
frontiers_tag=$(get_latest_tag "n00-frontiers")
cortex_tag=$(get_latest_tag "n00-cortex")
n00t_tag=$(get_latest_tag "n00t")
n00tropic_tag=$(get_latest_tag "n00tropic")
n00plicate_tag=$(get_latest_tag "n00plicate")

release_version=${1:-"$(date +%Y.%m.%d)"}

log "Writing release manifest -> $MANIFEST"
mkdir -p "$DOCS_DIR"
{
	printf 'version: %s\n' "$release_version"
	printf 'generated: "%s"\n' "$(date --iso-8601=seconds 2>/dev/null || date)"
	printf 'repositories:\n'
	write_manifest_entry "n00-frontiers" "$frontiers_tag"
	write_manifest_entry "n00-cortex" "$cortex_tag"
	write_manifest_entry "n00t" "$n00t_tag"
	write_manifest_entry "n00tropic" "$n00tropic_tag"
	write_manifest_entry "n00plicate" "$n00plicate_tag"
} >"$MANIFEST"

log "Release manifest updated. Review tags and push once satisfied."
SUMMARY="Release manifest ${release_version} recorded"
