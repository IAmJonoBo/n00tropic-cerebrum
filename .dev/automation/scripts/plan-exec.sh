#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
ARTIFACT_DIR="$ROOT/.dev/automation/artifacts/plans"
mkdir -p "$ARTIFACT_DIR"

if [[ " $* " != *" --repo-root"* ]]; then
	EXTRA=("--repo-root" "$ROOT")
else
	EXTRA=()
fi

python3 -m n00t.planning.engine "${EXTRA[@]}" "$@"
