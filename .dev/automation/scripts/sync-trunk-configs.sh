#!/usr/bin/env bash
set -uo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
SCRIPT="$ROOT/.dev/automation/scripts/sync-trunk.py"

if [[ ! -x "$SCRIPT" ]]; then
  echo "[sync-trunk] Missing sync-trunk.py helper at $SCRIPT" >&2
  exit 2
fi

if [[ $# -eq 0 ]]; then
  set -- --check
fi

ARGS=()
for arg in "$@"; do
  case "$arg" in
    --write)
      ARGS+=(--pull)
      ;;
    --check)
      ARGS+=(--check)
      ;;
    *)
      ARGS+=("$arg")
      ;;
  esac
done

exec python3 "$SCRIPT" "${ARGS[@]}"
