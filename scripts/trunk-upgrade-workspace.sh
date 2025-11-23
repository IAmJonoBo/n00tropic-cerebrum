#!/usr/bin/env bash
set -euo pipefail

# Workspace-aware Trunk upgrade + config propagation.
# Usage: scripts/trunk-upgrade-workspace.sh [--check] [--fmt]
#
# - Ensures a trunk binary is available (respects TRUNK_BIN).
# - Runs `trunk upgrade --yes` to refresh plugins/linters.
# - Syncs canonical trunk configs into subrepos.
# - Optionally runs trunk checks across subrepos.
#
# Ephemeral runner note:
#   Provide TRUNK_BIN pointing at a preinstalled trunk, or set TRUNK_INSTALL=1
#   and ensure trunk is on PATH (installer may require sudo; prefer cached binary).

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEFAULT_TRUNK_BIN="${HOME}/.cache/trunk/bin/trunk"
TRUNK_BIN="${TRUNK_BIN:-${DEFAULT_TRUNK_BIN}}"

DO_CHECK=false
DO_FMT=false
for arg in "$@"; do
	case "$arg" in
	--check) DO_CHECK=true ;;
	--fmt) DO_FMT=true ;;
	-h | --help)
		echo "Usage: $0 [--check] [--fmt]"
		exit 0
		;;
	esac
done

ensure_trunk() {
	if [[ -x ${TRUNK_BIN} ]]; then
		return 0
	fi
	if command -v trunk >/dev/null 2>&1; then
		TRUNK_BIN="$(command -v trunk)"
		return 0
	fi
	echo "Trunk binary not found at ${TRUNK_BIN} or on PATH." >&2
	echo "Set TRUNK_BIN to an existing trunk binary or preinstall trunk (prefer cached path ${DEFAULT_TRUNK_BIN})." >&2
	exit 1
}

ensure_trunk

echo "Using trunk binary: ${TRUNK_BIN}"

pushd "${ROOT}" >/dev/null

echo "Upgrading trunk plugins/linters..."
"${TRUNK_BIN}" upgrade --yes || {
	echo "trunk upgrade failed; aborting." >&2
	exit 1
}

echo "Syncing canonical trunk configs into subrepos..."
node scripts/sync-trunk-defs.mjs --pull

if [[ ${DO_CHECK} == true ]]; then
	echo "Running trunk checks across subrepos..."
	TRUNK_BIN="${TRUNK_BIN}" .dev/automation/scripts/run-trunk-subrepos.sh $([[ ${DO_FMT} == true ]] && echo --fmt)
else
	echo "Skipping trunk checks (pass --check to run)."
fi

popd >/dev/null

echo "Trunk upgrade workflow completed."
