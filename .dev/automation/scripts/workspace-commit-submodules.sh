#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "${ROOT_DIR}"

MESSAGE=${1:-"chore(workspace): update submodule SHAs"}

echo "[workspace-commit-submodules] Root: ${ROOT_DIR}"

echo "[workspace-commit-submodules] Checking submodule status..."
git submodule status || true

echo
read -r -p "Stage all submodules in root and commit with message '${MESSAGE}'? [y/N] " answer
case "${answer-}" in
[Yy]*) ;;
*)
	echo "Aborted."
	exit 1
	;;
esac

# Stage all submodules as paths in the root repo
while IFS= read -r path; do
	if [[ -n "${path}" ]]; then
		echo "[workspace-commit-submodules] Staging ${path}"
		git add "${path}"
	fi
done < <(git config --file .gitmodules --get-regexp '^submodule\..*\.path$' | awk '{print $2}')

if git diff --cached --quiet; then
	echo "[workspace-commit-submodules] No submodule pointer changes to commit."
	exit 0
fi

echo "[workspace-commit-submodules] Committing..."
git commit -m "${MESSAGE}"

echo "[workspace-commit-submodules] Done. You can now run 'git push'."
