#!/usr/bin/env bash
set -euo pipefail

PIN=${PIN:-10.23.0}
STORE=".pnpm-store"

if [[ ! -d $STORE ]]; then
	echo "[pnpm-store] $STORE not found; skip"
	exit 0
fi

bad=$(find "$STORE" -path '*files/*' -type f -print | grep -v "$PIN" || true)

if [[ -n $bad ]]; then
	echo "[pnpm-store] drift detected (expected pnpm@$PIN):"
	echo "$bad"
	exit 1
fi

echo "[pnpm-store] OK (pin=$PIN)"
