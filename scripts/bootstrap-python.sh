#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
REQ_FULL="$ROOT_DIR/requirements.workspace.txt"
LOCK_FULL="$ROOT_DIR/requirements.workspace.lock"
REQ_MIN="$ROOT_DIR/requirements.workspace.min.txt"
LOCK_MIN="$ROOT_DIR/requirements.workspace.min.lock"

PYTHON_BIN=${PYTHON_BIN:-python3}
VENV_PATH=${WORKSPACE_VENV:-"$ROOT_DIR/.venv-workspace"}

USE_FULL=false
REQ_OVERRIDE=${WORKSPACE_REQUIREMENTS_FILE-}
LOCK_OVERRIDE=${WORKSPACE_LOCK_FILE-}

usage() {
	cat <<'EOF'
Usage: scripts/bootstrap-python.sh [--full]
  --full   Install all subproject deps (agents, OCR, Jupyter, azure agent preview)
By default, a minimal set is installed (n00tropic + n00-school + mcp docs server + pip-audit).
Override with WORKSPACE_REQUIREMENTS_FILE / WORKSPACE_LOCK_FILE env vars if needed.
EOF
}

while [[ $# -gt 0 ]]; do
	case "$1" in
	--full) USE_FULL=true ;;
	-h | --help)
		usage
		exit 0
		;;
	*)
		echo "[bootstrap-python] unknown flag: $1" >&2
		usage
		exit 1
		;;
	esac
	shift
done

if [[ -n $REQ_OVERRIDE ]]; then
	REQUIREMENTS_FILE="$REQ_OVERRIDE"
	LOCK_FILE="${LOCK_OVERRIDE:-${REQUIREMENTS_FILE%.txt}.lock}"
elif $USE_FULL; then
	REQUIREMENTS_FILE="$REQ_FULL"
	LOCK_FILE="$LOCK_FULL"
else
	REQUIREMENTS_FILE="$REQ_MIN"
	LOCK_FILE="$LOCK_MIN"
fi

if [[ ! -f $REQUIREMENTS_FILE ]]; then
	echo "[bootstrap-python] requirements file not found at $REQUIREMENTS_FILE" >&2
	exit 1
fi

PATH="$HOME/.local/bin:$PATH" # ensure uv from user install is discoverable
export UV_CACHE_DIR=${UV_CACHE_DIR:-"$ROOT_DIR/.cache/uv"}
mkdir -p "$UV_CACHE_DIR"

ensure_uv() {
	if command -v uv >/dev/null 2>&1; then
		return 0
	fi
	echo "[bootstrap-python] uv not found; installing via https://astral.sh/uv/install.sh" >&2
	local install_log
	install_log=$(mktemp)
	if command -v curl >/dev/null 2>&1; then
		curl -LsSf https://astral.sh/uv/install.sh | sh >>"$install_log" 2>&1 || return 1
	elif command -v wget >/dev/null 2>&1; then
		wget -qO- https://astral.sh/uv/install.sh | sh >>"$install_log" 2>&1 || return 1
	else
		echo "[bootstrap-python] curl/wget unavailable; cannot install uv" >&2
		return 1
	fi
	hash -r
	if command -v uv >/dev/null 2>&1; then
		echo "[bootstrap-python] uv installed (log: $install_log)"
		return 0
	fi
	echo "[bootstrap-python] uv installation failed; see $install_log" >&2
	return 1
}

if ensure_uv; then
	UV_BIN=$(command -v uv)
	echo "[bootstrap-python] using uv to provision venv + sync dependencies"
	"$UV_BIN" venv "$VENV_PATH"
	. "$VENV_PATH/bin/activate"
	if [[ -f $LOCK_FILE ]]; then
		echo "[bootstrap-python] syncing from lock: $LOCK_FILE"
		"$UV_BIN" pip sync "$LOCK_FILE"
	else
		echo "[bootstrap-python] lock file missing; syncing from $REQUIREMENTS_FILE"
		"$UV_BIN" pip sync "$REQUIREMENTS_FILE"
	fi
else
	echo "[bootstrap-python] uv unavailable; falling back to python venv + pip (slower, less reproducible)" >&2
	if [[ ! -d $VENV_PATH ]]; then
		echo "[bootstrap-python] creating virtual environment at $VENV_PATH"
		"$PYTHON_BIN" -m venv "$VENV_PATH"
	fi
	# shellcheck disable=SC1090
	source "$VENV_PATH/bin/activate"
	python -m pip install --upgrade pip
	if [[ -f $LOCK_FILE ]]; then
		echo "[bootstrap-python] installing from lock: $LOCK_FILE"
		python -m pip install --upgrade -r "$LOCK_FILE"
	else
		python -m pip install --upgrade -r "$REQUIREMENTS_FILE"
	fi
fi

echo "[bootstrap-python] workspace dependencies installed. Activate via:"
echo "source $VENV_PATH/bin/activate"
