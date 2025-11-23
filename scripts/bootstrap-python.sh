#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
REQUIREMENTS_FILE="$ROOT_DIR/requirements.workspace.txt"
if [[ ! -f $REQUIREMENTS_FILE ]]; then
	echo "[bootstrap-python] requirements file not found at $REQUIREMENTS_FILE" >&2
	exit 1
fi

PYTHON_BIN=${PYTHON_BIN:-python3}
VENV_PATH=${WORKSPACE_VENV:-"$ROOT_DIR/.venv-workspace"}
LOCK_FILE="$ROOT_DIR/requirements.workspace.lock"

use_uv() {
	command -v uv >/dev/null 2>&1
}

if use_uv; then
	echo "[bootstrap-python] using uv to provision venv + sync dependencies"
	uv venv "$VENV_PATH"
	. "$VENV_PATH/bin/activate"
	if [[ -f $LOCK_FILE ]]; then
		echo "[bootstrap-python] syncing from lock: $LOCK_FILE"
		uv pip sync "$LOCK_FILE"
	else
		echo "[bootstrap-python] lock file missing; syncing from $REQUIREMENTS_FILE"
		uv pip sync "$REQUIREMENTS_FILE"
	fi
else
	echo "[bootstrap-python] uv not found; falling back to python venv + pip (install uv for faster, reproducible sync)"
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
