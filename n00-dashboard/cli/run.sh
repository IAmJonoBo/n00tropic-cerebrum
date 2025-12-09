#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

if ! command -v swift >/dev/null 2>&1; then
	echo "[n00-dashboard] swift is not installed. Install Xcode 16+ or Swift 5.10+." >&2
	exit 1
fi

cd "$ROOT_DIR"
echo "[n00-dashboard] Building and running DashboardApp via SwiftPM"
swift run DashboardApp "$@"
