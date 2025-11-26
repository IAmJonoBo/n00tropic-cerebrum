#!/usr/bin/env bash
set -euo pipefail

# Workspace-wide QA helper that chains the canonical meta-check and optional Trunk sweeps.
# Usage: scripts/workspace-qa.sh [--full] [--with-trunk] [--fmt] [--auto-fix] [--meta-only]

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
META_CHECK="$ROOT/.dev/automation/scripts/meta-check.sh"
TRUNK_SWEEP="$ROOT/.dev/automation/scripts/run-trunk-subrepos.sh"

AUTO_FIX=0
RUN_TRUNK=0
RUN_META=1
DO_FMT=0

usage() {
	cat <<'USAGE'
Usage: scripts/workspace-qa.sh [options]

  --full         Run meta-check with auto-fix and a Trunk sweep (fmt + check).
  --with-trunk   Add a Trunk sweep after meta-check.
  --fmt          Format while running the Trunk sweep (implies --with-trunk).
  --auto-fix     Allow meta-check to run doctor + safe autofixes.
  --meta-only    Run meta-check only (skip Trunk sweep).
  -h, --help     Show this help.

Examples:
  scripts/workspace-qa.sh               # doctor + meta-check only
  scripts/workspace-qa.sh --full        # doctor+autofix, then trunk check --fmt
  scripts/workspace-qa.sh --with-trunk  # doctor + trunk check without formatting
USAGE
}

while [[ $# -gt 0 ]]; do
	case "$1" in
	--full)
		AUTO_FIX=1
		RUN_TRUNK=1
		DO_FMT=1
		;;
	--with-trunk)
		RUN_TRUNK=1
		;;
	--fmt)
		RUN_TRUNK=1
		DO_FMT=1
		;;
	--auto-fix)
		AUTO_FIX=1
		;;
	--meta-only)
		RUN_TRUNK=0
		;;
	-h | --help)
		usage
		exit 0
		;;
	*)
		echo "[workspace-qa] Unknown flag: $1" >&2
		usage
		exit 2
		;;
	esac
	shift
done

status=0

if [[ $RUN_META -eq 1 ]]; then
	if [[ ! -x $META_CHECK ]]; then
		echo "[workspace-qa] meta-check helper missing at $META_CHECK" >&2
		status=1
	else
		echo "[workspace-qa] Running meta-check (auto-fix=${AUTO_FIX})"
		META_FLAGS=("--doctor")
		if [[ $AUTO_FIX -eq 1 ]]; then
			META_FLAGS=("--auto-fix")
		fi
		if ! "$META_CHECK" "${META_FLAGS[@]}"; then
			status=1
		fi
	fi
fi

if [[ $RUN_TRUNK -eq 1 ]]; then
	if [[ ! -x $TRUNK_SWEEP ]]; then
		echo "[workspace-qa] Trunk sweep helper missing at $TRUNK_SWEEP" >&2
		status=1
	else
		echo "[workspace-qa] Running Trunk sweep across subrepos (fmt=${DO_FMT})"
		TRUNK_FLAGS=()
		if [[ $DO_FMT -eq 1 ]]; then
			TRUNK_FLAGS+=("--fmt")
		fi
		if ! "$TRUNK_SWEEP" "${TRUNK_FLAGS[@]}"; then
			status=1
		fi
	fi
fi

exit $status
