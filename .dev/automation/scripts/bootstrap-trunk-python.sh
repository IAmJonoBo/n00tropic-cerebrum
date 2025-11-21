#!/usr/bin/env bash
set -euo pipefail

# Trunk is configured to allow system runtimes (see n00-frontiers/.trunk/trunk.yaml).
# This script is kept for backwards compatibility but simply exits after logging.

echo "[bootstrap-trunk-python] Skipping hermetic runtime download; using system runtimes."
exit 0
