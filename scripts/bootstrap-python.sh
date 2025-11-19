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

if [[ ! -d $VENV_PATH ]]; then
	echo "[bootstrap-python] creating virtual environment at $VENV_PATH"
	"$PYTHON_BIN" -m venv "$VENV_PATH"
fi

# shellcheck disable=SC1090
source "$VENV_PATH/bin/activate"
python -m pip install --upgrade pip
python -m pip install --upgrade -r "$REQUIREMENTS_FILE"

echo "[bootstrap-python] workspace dependencies installed. Activate via:"
echo "source $VENV_PATH/bin/activate"
