#!/usr/bin/env bash
# Remove old actions-runner backups (keeps newest two).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

pattern="actions-runner.bak-*"
mapfile -t backups < <(ls -dt ${pattern} 2>/dev/null || true)

if [[ ${#backups[@]} -le 2 ]]; then
	echo "[runner-prune-backups] nothing to prune (found ${#backups[@]} backups)"
	exit 0
fi

keep=("${backups[@]:0:2}")
prune=("${backups[@]:2}")

echo "[runner-prune-backups] keeping: ${keep[*]:-none}"
echo "[runner-prune-backups] pruning: ${prune[*]}"
for d in "${prune[@]}"; do
	rm -rf "$d"
done
echo "[runner-prune-backups] done"
