#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
PY_VERSION_FILE="$ROOT_DIR/.python-version"
if [[ ! -f $PY_VERSION_FILE ]]; then
	echo "workspace .python-version missing at $PY_VERSION_FILE" >&2
	exit 1
fi
OVERRIDE_DIR="$ROOT_DIR/n00-cortex/data/dependency-overrides"
get_override_version() {
	local repo="$1"
	python3 - "$OVERRIDE_DIR" "$repo" <<'PY'
import json
import sys
from pathlib import Path

override_dir = Path(sys.argv[1])
repo = sys.argv[2]
tool = "python"
path = override_dir / f"{repo}.json"
if not path.exists():
    raise SystemExit(0)
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(0)
entry = (data.get("overrides") or {}).get(tool)
if isinstance(entry, dict):
    value = entry.get("version")
    if isinstance(value, str):
        print(value)
PY
}

REPOS=(
	n00-frontiers
	n00-cortex
	n00clear-fusion
	n00-school
	n00-horizons
	n00tropic
	n00t
)
for repo in "${REPOS[@]}"; do
	target="$ROOT_DIR/$repo/.python-version"
	if [[ ! -d $ROOT_DIR/$repo ]]; then
		echo "skip $repo (missing dir)"
		continue
	fi
	override_version="$(get_override_version "$repo" || true)"
	if [[ -n $override_version ]]; then
		rm -f "$target"
		printf "%s\n" "$override_version" >"$target"
		echo "pinned $target to override python $override_version"
	else
		ln -sfn ../.python-version "$target"
		echo "linked $target -> ../.python-version"
	fi
done
