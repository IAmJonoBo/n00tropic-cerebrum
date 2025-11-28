#!/usr/bin/env bash
# Simple uv-first bootstrap for any Python subrepo.
# Usage: scripts/uv-bootstrap.sh <repo-path>
# - Creates .uv-cache inside the repo (or uses existing UV_CACHE_DIR)
# - Creates .venv with uv if missing
# - Installs requirements.txt and requirements-dev.txt if present

set -euo pipefail

repo_root="${1:-}"
if [[ -z ${repo_root} ]]; then
	echo "Usage: $0 <repo-path>" >&2
	exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
	echo "uv is required but not installed. Install from https://github.com/astral-sh/uv and retry." >&2
	exit 1
fi

repo_root="$(cd "${repo_root}" && pwd)"
export UV_CACHE_DIR="${UV_CACHE_DIR:-${repo_root}/.uv-cache}"

cd "${repo_root}"

if [[ ! -d .venv ]]; then
	echo "[uv-bootstrap] creating .venv in ${repo_root}"
	uv venv .venv
else
	echo "[uv-bootstrap] reusing existing .venv in ${repo_root}"
fi

install_if_exists() {
	local file="$1"
	if [[ -f ${file} ]]; then
		echo "[uv-bootstrap] installing ${file}"
		UV_CACHE_DIR="${UV_CACHE_DIR}" uv pip install -r "${file}"
	fi
}

install_if_exists requirements.txt
install_if_exists requirements-dev.txt

echo "[uv-bootstrap] done. Activate with: source ${repo_root}/.venv/bin/activate"
