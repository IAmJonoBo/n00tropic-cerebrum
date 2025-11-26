#!/usr/bin/env bash
# Fetch syft into ./bin if missing. Kept out of git via .gitignore.
set -euo pipefail

# Default to a cache directory without spaces to avoid installer parsing issues
BIN_DIR="${SYFT_INSTALL_DIR:-$HOME/.cache/n00tropic-syft/bin}"
mkdir -p "${BIN_DIR}"

if command -v syft >/dev/null 2>&1; then
	echo "syft already in PATH: $(command -v syft)"
	exit 0
fi

if [[ -x "${BIN_DIR}/syft" ]]; then
	echo "syft already present at ${BIN_DIR}/syft"
	exit 0
fi

echo "Installing syft to ${BIN_DIR}..."
tmp_script=$(mktemp)
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh -o "$tmp_script"
bash "$tmp_script" -b "$BIN_DIR"
rm -f "$tmp_script"
echo "syft installed at ${BIN_DIR}/syft"
