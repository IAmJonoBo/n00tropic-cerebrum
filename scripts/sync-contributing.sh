#!/usr/bin/env bash
set -euo pipefail

# Propagate the workspace CONTRIBUTING.md into each submodule root and refresh the
# VS Code workspace file so subrepos appear automatically in Explorer/SCM.

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SOURCE="$ROOT/CONTRIBUTING.md"
WORKSPACE_FILE="$ROOT/n00tropic-cerebrum.code-workspace"
WRITE=0

while [[ $# -gt 0 ]]; do
	case "$1" in
	--write)
		WRITE=1
		;;
	-h | --help)
		cat <<'USAGE'
Usage: scripts/sync-contributing.sh [--write]
  --write   Actually copy the CONTRIBUTING.md into submodules and rewrite the workspace file (default: dry-run)
USAGE
		exit 0
		;;
	*)
		echo "[sync-contributing] Unknown arg: $1" >&2
		exit 2
		;;
	esac
	shift
done

if [[ ! -f $SOURCE ]]; then
	echo "[sync-contributing] Missing $SOURCE" >&2
	exit 1
fi

submodules=$(git config -f "$ROOT/.gitmodules" --get-regexp '^submodule\..*\.path' | awk '{print $2}')
if [[ -z $submodules ]]; then
	echo "[sync-contributing] No submodules found" >&2
	exit 0
fi

# Rebuild VS Code workspace descriptor from current submodule list
tmp_ws=$(mktemp)
{
	echo '{'
	echo '  "folders": ['
	echo '    { "path": "." },'
	idx=0
	for path in $submodules; do
		idx=$((idx + 1))
		sep=","
		[[ $idx -eq $(echo "$submodules" | wc -w) ]] && sep=""
		echo "    { \"path\": \"$path\" }$sep"
	done
	cat <<'JSON'
  ],
  "settings": {
    "files.exclude": {
      "**/.git": true,
      "**/.trunk": true,
      "**/.venv": true,
      "**/node_modules": false
    }
  }
}
JSON
} >"$tmp_ws"

if [[ $WRITE -eq 1 ]]; then
	mv "$tmp_ws" "$WORKSPACE_FILE"
	echo "[sync-contributing] Regenerated VS Code workspace file"
else
	echo "[sync-contributing] Would regenerate VS Code workspace file (run with --write)"
	rm "$tmp_ws"
fi

for path in $submodules; do
	target="$ROOT/$path/CONTRIBUTING.md"
	if [[ -f $target ]] && cmp -s "$SOURCE" "$target"; then
		echo "[sync-contributing] $path already up to date"
		continue
	fi
	if [[ $WRITE -eq 1 ]]; then
		cp "$SOURCE" "$target"
		echo "[sync-contributing] Updated $path/CONTRIBUTING.md"
	else
		echo "[sync-contributing] Would update $path/CONTRIBUTING.md (run with --write)"
	fi
done
