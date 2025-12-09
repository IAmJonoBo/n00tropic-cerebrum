#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
hook_src="$root_dir/.git/hooks/pre-push"

if [[ ! -f $hook_src ]]; then
	echo "pre-push hook not found at $hook_src" >&2
	exit 1
fi

install_hook() {
	local repo_path="$1"
	if ! git -C "$repo_path" rev-parse --git-dir >/dev/null 2>&1; then
		echo "[skip] $repo_path is not a git repo" >&2
		return
	fi
	local hooks_dir
	hooks_dir="$(git -C "$repo_path" rev-parse --git-path hooks)"
	mkdir -p "$hooks_dir"
	if cmp -s "$hook_src" "$hooks_dir/pre-push" 2>/dev/null; then
		echo "[up-to-date] $hooks_dir/pre-push"
	else
		cp "$hook_src" "$hooks_dir/pre-push"
		chmod +x "$hooks_dir/pre-push"
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
