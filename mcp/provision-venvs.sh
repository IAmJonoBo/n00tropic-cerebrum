#!/usr/bin/env bash
# Ensure the MCP virtual environments are provisioned with the expected lockfiles.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
UV_BIN="${UV_BIN-}"

if [[ -z ${UV_BIN} ]]; then
	if command -v uv >/dev/null 2>&1; then
		UV_BIN="$(command -v uv)"
	else
		echo "[mcp] uv is required. Install with: pip install uv" >&2
		exit 1
	fi
fi

create_venv() {
	local target="$1"
	if [[ -d ${target} ]]; then
		return
	fi
	echo "[mcp] creating virtualenv at ${target}"
	python3 -m venv "${target}"
}

sync_env() {
	local venv_path="$1"
	local lockfile="$2"
	if [[ ! -f "${ROOT}/${lockfile}" ]]; then
		echo "[mcp] missing lockfile ${lockfile}" >&2
		exit 1
	fi
	local interpreter="${venv_path}/bin/python"
	if [[ ! -x ${interpreter} ]]; then
		echo "[mcp] interpreter not found for ${venv_path}" >&2
		exit 1
	fi
	echo "[mcp] syncing ${venv_path} with ${lockfile}"
	UV_LINK_MODE="copy" "${UV_BIN}" pip sync -p "${interpreter}" "${ROOT}/${lockfile}"
}

create_venv "${ROOT}/.venv"
create_venv "${ROOT}/.venv-workspace"

sync_env "${ROOT}/.venv" "requirements.workspace.min.lock"
sync_env "${ROOT}/.venv-workspace" "requirements.workspace.lock"

echo "[mcp] environments provisioned"
