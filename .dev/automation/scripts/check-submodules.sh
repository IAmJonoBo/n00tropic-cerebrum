#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)

cd "$ROOT"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
	echo "[check-submodules] Not inside a git repository: $ROOT" >&2
	exit 1
fi

if ! git config -f .gitmodules --get-regexp '^submodule\.' >/dev/null 2>&1; then
	echo "[check-submodules] No submodules defined. Nothing to verify."
	exit 0
fi

declare -i dirty=0

while IFS= read -r line; do
	name=$(awk '{print $1}' <<<"$line" | sed -E 's/^submodule\.([^.]*)\.path$/\1/')
	submodule_path=$(awk '{print $2}' <<<"$line")
	expected_branch=$(git config -f .gitmodules "submodule.${name}.branch" || echo "main")
	current_branch=$(git -C "$submodule_path" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "detached")
	status_output=$(git -C "$submodule_path" status --short)
	if [[ -n $status_output ]]; then
		echo "[check-submodules] Detected uncommitted changes in '$submodule_path':"
		echo "$status_output"
		dirty=1
	fi
	if [[ $current_branch == "HEAD" || $current_branch == "detached" ]]; then
		echo "[check-submodules] Submodule '$submodule_path' is in a detached HEAD; switch to $expected_branch."
		dirty=1
	fi
	if [[ $current_branch != "$expected_branch" ]]; then
		echo "[check-submodules] Submodule '$submodule_path' on branch '$current_branch' but expected '$expected_branch' per .gitmodules."
		dirty=1
	fi
	# Detect divergence from recorded commit
	recorded_rev=$(git ls-tree HEAD "$submodule_path" | awk '{print $3}')
	current_rev=$(git -C "$submodule_path" rev-parse HEAD)
	if [[ $recorded_rev != "$current_rev" ]]; then
		echo "[check-submodules] Submodule '$submodule_path' HEAD ($current_rev) differs from superproject reference ($recorded_rev). Stage and commit the update."
		dirty=1
	fi
	# Detect ahead/behind vs upstream
	if git -C "$submodule_path" rev-list --left-right --count "origin/${expected_branch}"...HEAD >/dev/null 2>&1; then
		read -r behind ahead < <(git -C "$submodule_path" rev-list --left-right --count "origin/${expected_branch}"...HEAD | awk '{print $1" "$2}')
		if ((ahead > 0)); then
			echo "[check-submodules] Submodule '$submodule_path' has $ahead local commit(s) not pushed to origin/${expected_branch}."
			dirty=1
		fi
		if ((behind > 0)); then
			echo "[check-submodules] Submodule '$submodule_path' is $behind commit(s) behind origin/${expected_branch}; pull before releasing."
			dirty=1
		fi
	fi
done < <(git config -f .gitmodules --get-regexp '^submodule\..*\.path')

if ((dirty)); then
	echo "[check-submodules] ❌ Submodule issues detected. Resolve before committing or releasing." >&2
	exit 2
fi

echo "[check-submodules] ✅ All submodules clean and synced."
