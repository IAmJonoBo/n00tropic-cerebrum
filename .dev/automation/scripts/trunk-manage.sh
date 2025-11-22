#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PY_SYNC="${ROOT}/.dev/automation/scripts/sync-trunk.py"
TRUNK_UPGRADE="${ROOT}/.dev/automation/scripts/trunk-upgrade.sh"
RUN_TRUNK_SUBREPOS="${ROOT}/.dev/automation/scripts/run-trunk-subrepos.sh"

usage() {
	cat <<'USAGE'
trunk-manage.sh <command> [args]

Commands:
  sync-check [--repo NAME...]     Check downstream .trunk/trunk.yaml matches canonical.
  sync-pull  [--repo NAME...]     Copy canonical trunk.yaml into downstream repos.
  sync-push  [--push-from NAME]   Promote a downstream trunk.yaml to canonical, then fan out.
  upgrade [--repo NAME...]        Run `trunk upgrade --no-progress` across repos.
  fmt [--fmt]                     Run trunk fmt across subrepos (delegates to run-trunk-subrepos.sh --fmt).
  check                           Alias for sync-check.

Notes:
  - Canonical config lives at n00-cortex/data/trunk/base/.trunk/trunk.yaml.
  - This script consolidates sync-trunk.py, trunk-upgrade.sh, and run-trunk-subrepos.sh entry points.
USAGE
}

if [[ $# -lt 1 ]]; then
	usage
	exit 1
fi

cmd="$1"
shift || true

case "${cmd}" in
sync-check | check)
	exec python3 "${PY_SYNC}" --check "$@"
	;;
sync-pull | pull | write)
	exec python3 "${PY_SYNC}" --pull "$@"
	;;
sync-push | push)
	exec python3 "${PY_SYNC}" --push "$@"
	;;
upgrade)
	exec "${TRUNK_UPGRADE}" "$@"
	;;
fmt | format)
	exec "${RUN_TRUNK_SUBREPOS}" --fmt "$@"
	;;
help | -h | --help)
	usage
	;;
*)
	echo "Unknown command: ${cmd}" >&2
	usage
	exit 1
	;;
esac
