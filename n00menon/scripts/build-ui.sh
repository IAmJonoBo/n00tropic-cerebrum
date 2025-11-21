#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
UI_SRC="${ROOT_DIR}/n00menon/ui"
OUT_DIR="${ROOT_DIR}/vendor/antora"
mkdir -p "${OUT_DIR}"
if [[ -d ${UI_SRC} ]]; then
	(cd "${UI_SRC}" && zip -r "${OUT_DIR}/ui-bundle.zip" . -q)
	echo "UI bundle created at ${OUT_DIR}/ui-bundle.zip"
else
	echo "UI source ${UI_SRC} does not exist"
	exit 1
fi
