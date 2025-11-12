#!/usr/bin/env bash
set -euo pipefail

# Create minimal stub Vale styles for local development to avoid "style not found" errors
# This is a local convenience helper; CI still uses the official Vale action which installs recommended styles.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STYLES_DIR="$ROOT_DIR/styles"

echo "Creating stub vale styles in $STYLES_DIR if missing"
mkdir -p "$STYLES_DIR"

create_stub() {
	STYLE_NAME="$1"
	if [ ! -d "$STYLES_DIR/$STYLE_NAME" ]; then
		mkdir -p "$STYLES_DIR/$STYLE_NAME"
		echo "# Stub style for $STYLE_NAME" >"$STYLES_DIR/$STYLE_NAME/README.md"
		# Minimal config file so Vale recognizes the folder; the real styles include rule YAML but those are not required for a stub
		cat >"$STYLES_DIR/$STYLE_NAME/Config.yml" <<EOF
Name: $STYLE_NAME
extends: []
EOF
		echo "Created stub style: $STYLE_NAME"
	else
		echo "Style $STYLE_NAME already exists; skipping"
	fi
}

## Only create n00 style stub; avoid creating common 'Google/Microsoft/Vale' stubs that can conflict with upstream style packs
create_stub n00
echo "Done. To run Vale locally with these stubs, run: vale docs"
