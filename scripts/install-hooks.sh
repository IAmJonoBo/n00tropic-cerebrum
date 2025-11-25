#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
hook_src="$root_dir/.git/hooks/pre-push"

if [[ ! -f "$hook_src" ]]; then
  echo "pre-push hook not found at $hook_src" >&2
  exit 1
fi

install_hook() {
  local repo_path="$1"
  if [[ ! -d "$repo_path/.git" ]]; then
    echo "[skip] $repo_path is not a git repo" >&2
    return
  fi
  mkdir -p "$repo_path/.git/hooks"
  if cmp -s "$hook_src" "$repo_path/.git/hooks/pre-push" 2>/dev/null; then
    echo "[up-to-date] $repo_path/.git/hooks/pre-push"
  else
    cp "$hook_src" "$repo_path/.git/hooks/pre-push"
    chmod +x "$repo_path/.git/hooks/pre-push"
    echo "[installed] pre-push in $repo_path"
  fi
}

# Install in superrepo
install_hook "$root_dir"

# Install in primary subrepos (edit list as needed)
for sub in n00-frontiers n00-cortex n00-horizons n00t n00-school n00menon n00plicate n00tropic n00clear-fusion; do
  if [[ -d "$root_dir/$sub" ]]; then
    install_hook "$root_dir/$sub"
  fi
done
