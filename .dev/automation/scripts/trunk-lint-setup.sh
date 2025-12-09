#!/usr/bin/env bash
# Install and (optionally) init Trunk without running lint. AGENT_HOOK: dependency-management
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
INSTALL_ALLOWED="${TRUNK_INSTALL:-${CI:-0}}"
RUN_INIT="${TRUNK_INIT_MISSING:-1}"

log() {
	printf '[trunk-setup] %s\n' "$1"
}

ensure_trunk_cli() {
	export PATH="$HOME/.trunk/bin:$PATH"
	if command -v trunk >/dev/null 2>&1; then
		return 0
	fi
	if [[ $INSTALL_ALLOWED != "1" ]]; then
		log "Trunk CLI not found. Set TRUNK_INSTALL=1 (or CI=1) to allow auto-install, or install manually from https://trunk.io."
		return 1
	fi
	if [[ ${TRUNK_INSTALL_SKIP:-0} == "1" ]]; then
		log "TRUNK_INSTALL_SKIP=1 set; refusing to install."
		return 1
	fi
	if ! command -v curl >/dev/null 2>&1; then
		log "curl missing; cannot install Trunk automatically."
		return 1
	fi
	log "Installing Trunk CLI (not detected)."
	local installer
	installer=$(mktemp)
	if curl -fsSL https://get.trunk.io -o "$installer"; then
		if ! bash "$installer" -y >/dev/null 2>&1; then
			log "Installer with -y failed; retrying interactively."
			bash "$installer" >/dev/null 2>&1 || {
				log "Trunk installer failed."
				rm -f "$installer"
				return 1
			}
		fi
		rm -f "$installer"
	else
		log "Failed to download installer."
		rm -f "$installer"
		return 1
	fi

	if ! command -v trunk >/dev/null 2>&1; then
		log "Trunk still unavailable after install attempt."
		return 1
	fi
	log "Trunk CLI installed."
	return 0
}

init_if_missing() {
	if [[ $RUN_INIT != "1" ]]; then
		return 0
	fi
	if [[ -f "${ROOT_DIR}/.trunk/trunk.yaml" ]]; then
		log "Trunk already initialized in root."
		return 0
	fi
	log "Initializing Trunk in repository root (.trunk/trunk.yaml missing)."
	TRUNK_NO_PROGRESS=1 TRUNK_DISABLE_TELEMETRY=1 TRUNK_NONINTERACTIVE=1 \
		trunk init --ci --no-progress
}

ensure_trunk_cli
init_if_missing
log "Done."
