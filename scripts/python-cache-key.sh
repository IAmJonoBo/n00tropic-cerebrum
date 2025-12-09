#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
LOCK_MIN="$ROOT_DIR/requirements.workspace.min.lock"
LOCK_FULL="$ROOT_DIR/requirements.workspace.lock"

scope="minimal"
[[ ${1-} == "--full" ]] && scope="full"

lock=$LOCK_MIN
[[ $scope == "full" ]] && lock=$LOCK_FULL

if [[ ! -f $lock ]]; then
	echo "missing lockfile: $lock" >&2
	exit 1
fi

hash=$(sha256sum "$lock" | awk '{print $1}')
echo "python-uv-cache-${scope}-${hash}"
