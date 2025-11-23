#!/usr/bin/env bash
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
TEMPLATE="$ROOT/.env.example"
FORCE=0

if [[ ! -f $TEMPLATE ]]; then
  echo "missing $TEMPLATE" >&2
  exit 1
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=1 ; shift ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

repos=()
if [[ -f "$ROOT/.gitmodules" ]]; then
  while IFS= read -r line; do
    [[ $line =~ path\ =\ (.+)$ ]] && repos+=("${BASH_REMATCH[1]}")
  done < <(grep -E "^\s*path\s*=\s*" "$ROOT/.gitmodules")
fi

# include workspace root as first target
repos=("." "${repos[@]}")

for r in "${repos[@]}"; do
  dest="$ROOT/$r/.env.example"
  if [[ -f $dest && $FORCE -eq 0 ]]; then
    echo "skip $dest (exists)"
    continue
  fi
  mkdir -p "$ROOT/$r"
  cp "$TEMPLATE" "$dest"
  echo "synced $dest"
  # ensure .env is ignored locally
  if ! grep -q '^\.env$' "$ROOT/$r/.gitignore" 2>/dev/null; then
    echo ".env" >> "$ROOT/$r/.gitignore"
  fi
  if ! grep -q '^\.env\.local$' "$ROOT/$r/.gitignore" 2>/dev/null; then
    echo ".env.local" >> "$ROOT/$r/.gitignore"
  fi
  # create stub .env if absent to hint users (empty, untracked because .gitignore)
  if [[ ! -f "$ROOT/$r/.env" ]]; then
    touch "$ROOT/$r/.env"
  fi
done
