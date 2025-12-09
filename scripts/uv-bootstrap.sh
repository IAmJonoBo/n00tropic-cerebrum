#!/usr/bin/env bash
# Simple uv-first bootstrap for any Python subrepo.
# Usage: scripts/uv-bootstrap.sh <repo-path>
# - Creates .uv-cache inside the repo (or uses existing UV_CACHE_DIR)
# - Creates .venv with uv if missing
# - Installs requirements.txt and requirements-dev.txt if present

set -euo pipefail

repo_root="${1-}"
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

find_trunk_root() {
	local dir="$1"
	while [[ ${dir} != "/" ]]; do
		if [[ -f "${dir}/.trunk/trunk.yaml" ]]; then
			echo "${dir}"
			return 0
		fi
		dir="$(dirname "${dir}")"
	done
	return 1
}

refresh_trunk() {
	if ! command -v trunk >/dev/null 2>&1; then
		echo "[uv-bootstrap] trunk not installed; skipping trunk upgrade"
		return 0
	fi

	local trunk_root
	if ! trunk_root=$(find_trunk_root "${repo_root}"); then
		echo "[uv-bootstrap] no .trunk/trunk.yaml found above ${repo_root}; skipping trunk upgrade"
		return 0
	fi

	echo "[uv-bootstrap] refreshing trunk tools in ${trunk_root}"
	(
		cd "${trunk_root}"
		TRUNK_DAEMON_DISABLED=1 \
			TRUNK_NO_ANALYTICS=1 \
			TRUNK_DISABLE_TELEMETRY=1 \
			TRUNK_NO_PROGRESS=1 \
			trunk upgrade --yes-to-all --ci --no-progress
	)
}

install_if_exists() {
	local file="$1"
	if [[ -f ${file} ]]; then
		echo "[uv-bootstrap] installing ${file}"
		UV_CACHE_DIR="${UV_CACHE_DIR}" uv pip install -r "${file}"
	fi
}

install_if_exists requirements.txt
install_if_exists requirements-dev.txt

refresh_trunk

echo "[uv-bootstrap] done. Activate with: source ${repo_root}/.venv/bin/activate"
