#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
REQ="$ROOT_DIR/requirements.workspace.txt"
LOCK="$ROOT_DIR/requirements.workspace.lock"

if [[ ! -f $REQ ]]; then
	echo "requirements file not found: $REQ" >&2
	exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
	echo "uv is required. Install via: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
	exit 1
fi

if [[ ${1-} == "--check" ]]; then
	tmp=$(mktemp)
	trap 'rm -f "$tmp"' EXIT
	uv pip compile "$REQ" -o "$tmp"
	if ! diff -u "$LOCK" "$tmp" >/dev/null 2>&1; then
		echo "requirements.workspace.lock is out of date" >&2
		diff -u "$LOCK" "$tmp" || true
		exit 1
	fi
	echo "Lockfile is up to date"
	exit 0
fi

echo "Rebuilding $LOCK with uv..."
uv pip compile "$REQ" -o "$LOCK"

echo "Done. If in CI, remember to commit the updated lockfile."
