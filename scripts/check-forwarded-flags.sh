#!/usr/bin/env bash
set -euo pipefail

# Scan package.json scripts for common pnpm CLI flags that when used with `pnpm run` will be forwarded
# to the underlying scripts and likely cause problems (e.g., --reporter, --workspace-concurrency)

echo "Scanning package.json scripts for forwarded pnpm flags..."

for f in $(git ls-files "**/package.json"); do
	if rg -q --hidden --no-ignore-vcs --glob '!node_modules' "(--workspace-concurrency|--reporter|--filter\\s|--filter='|--if-present)" "$f"; then
		echo "[WARN] $f contains possibly forwarded pnpm flags in scripts:"
		rg -n --hidden --no-ignore-vcs --glob '!node_modules' "(--workspace-concurrency|--reporter|--filter\\s|--filter='|--filter=\"|--if-present)" "$f" || true
		echo
	fi
done

echo "Scan complete. Review warnings and consider moving workspace flags into root pnpm invocations or adjusting scripts to avoid forwarding flags."
