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
	submodule_path=$(awk '{print $2}' <<<"$line")
	status_output=$(git -C "$submodule_path" status --short)
	if [[ -n $status_output ]]; then
		echo "[check-submodules] Detected uncommitted changes in '$submodule_path':"
		echo "$status_output"
		dirty=1
	fi
	# Detect divergence from recorded commit
	recorded_rev=$(git ls-tree HEAD "$submodule_path" | awk '{print $3}')
	current_rev=$(git -C "$submodule_path" rev-parse HEAD)
	if [[ $recorded_rev != "$current_rev" ]]; then
		echo "[check-submodules] Submodule '$submodule_path' HEAD ($current_rev) differs from superproject reference ($recorded_rev). Stage and commit the update."
		dirty=1
	fi
	# Warn about unpushed commits
	if git -C "$submodule_path" rev-list --left-right --count origin/"$(git -C "$submodule_path" rev-parse --abbrev-ref HEAD)"...HEAD >/dev/null 2>&1; then
		ahead=$(git -C "$submodule_path" rev-list --left-right --count origin/"$(git -C "$submodule_path" rev-parse --abbrev-ref HEAD)"...HEAD | awk '{print $2}')
		if ((ahead > 0)); then
			echo "[check-submodules] Submodule '$submodule_path' has $ahead local commit(s) not pushed to origin."
			dirty=1
		fi
	fi
done < <(git config -f .gitmodules --get-regexp '^submodule\..*\.path' | awk '{print $2}')

if ((dirty)); then
	echo "[check-submodules] ❌ Submodule issues detected. Resolve before committing or releasing." >&2
	exit 2
fi

echo "[check-submodules] ✅ All submodules clean and synced."
