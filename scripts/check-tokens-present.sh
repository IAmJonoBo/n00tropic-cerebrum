#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TOKENS_PATH="$ROOT_DIR/n00plicate/packages/design-tokens/libs/tokens/json/tokens.json"
ALT_PATH="$ROOT_DIR/n00plicate/tokens.json"

if [[ ! -f $TOKENS_PATH && -f $ALT_PATH ]]; then
	TOKENS_PATH="$ALT_PATH"
fi

if [[ ! -f $TOKENS_PATH ]]; then
	echo "[check-tokens-present] tokens.json missing; expected at n00plicate/packages/design-tokens/libs/tokens/json/tokens.json (or symlink)" >&2
	exit 1
fi

size=$(stat -f%z "$TOKENS_PATH" 2>/dev/null || stat -c%s "$TOKENS_PATH")
echo "[check-tokens-present] tokens present at $(realpath "$TOKENS_PATH") (size=${size} bytes)"

# Warn but do not fail on empty files to allow placeholder exports pre-release
if [[ ${size:-0} -eq 0 ]]; then
	echo "[check-tokens-present] warning: tokens file is empty; replace with real Penpot export before release" >&2
fi
