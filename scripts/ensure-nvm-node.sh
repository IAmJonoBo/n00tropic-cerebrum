#!/usr/bin/env bash
# Ensure the shell is using the Node version pinned in the workspace .nvmrc.
# Safe when nvm is missing: logs a warning and continues.

set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
NVMRC_FILE="$ROOT_DIR/.nvmrc"

if [[ ! -f $NVMRC_FILE ]]; then
	echo "[ensure-nvm-node] No .nvmrc at $NVMRC_FILE; skipping" >&2
	return 0 2>/dev/null || exit 0
fi

PINNED_VERSION=$(cat "$NVMRC_FILE")
NVM_DIR=${NVM_DIR:-"$HOME/.nvm"}

# Load nvm if not already loaded
if ! command -v nvm >/dev/null 2>&1; then
	if [[ -s "$NVM_DIR/nvm.sh" ]]; then
		# shellcheck source=/dev/null
		. "$NVM_DIR/nvm.sh"
	fi
fi

if command -v nvm >/dev/null 2>&1; then
	nvm install "$PINNED_VERSION" >/dev/null
	nvm use "$PINNED_VERSION" >/dev/null
	echo "[ensure-nvm-node] Using Node $(node -v) (pinned $PINNED_VERSION)"
else
	echo "[ensure-nvm-node] nvm not found; expected Node $PINNED_VERSION. Install nvm to auto-switch." >&2
fi

return 0 2>/dev/null || exit 0
