#!/usr/bin/env bash
set -euo pipefail
DIR=$(cd "$(dirname "$0")/../../.." && pwd)
DEFAULT_TRUNK_BIN="${HOME}/.cache/trunk/bin/trunk"
TRUNK_BIN="${TRUNK_BIN:-${DEFAULT_TRUNK_BIN}}"
if [[ ! -x ${TRUNK_BIN} && -x "${HOME}/.trunk/bin/trunk" ]]; then
	TRUNK_BIN="${HOME}/.trunk/bin/trunk"
fi
echo "Using trunk binary at: ${TRUNK_BIN}"
export VALE_LOCAL=1
export VALE_CONFIG="${DIR}/.vale.local.ini"
echo "VALE_CONFIG=${VALE_CONFIG}"
cd "${DIR}"

# Resolve trunk binary if TRUNK_BIN path is not present
if [[ ! -x ${TRUNK_BIN} ]]; then
	if command -v trunk >/dev/null 2>&1; then
		TRUNK_BIN="$(command -v trunk)"
		echo "Resolved trunk binary via PATH: ${TRUNK_BIN}"
	else
		if [[ ${CI:-0} == 1 || ${TRUNK_INSTALL:-0} == 1 ]]; then
			echo "Trunk CLI missing; bootstrapping via trunk-upgrade.sh (install gated to CI/TRUNK_INSTALL=1)."
			if "${DIR}/.dev/automation/scripts/trunk-upgrade.sh"; then
				if command -v trunk >/dev/null 2>&1; then
					TRUNK_BIN="$(command -v trunk)"
					echo "Resolved trunk binary after bootstrap: ${TRUNK_BIN}"
				else
					echo "Trunk CLI still unavailable after bootstrap attempt." >&2
					exit 1
				fi
			else
				echo "Failed to install Trunk CLI via trunk-upgrade.sh" >&2
				exit 1
			fi
		else
			echo "Trunk binary missing at ${TRUNK_BIN} and not found on PATH." >&2
			echo "To avoid local installs by default, set TRUNK_BIN to an existing CLI or run 'TRUNK_INSTALL=1 .dev/automation/scripts/trunk-upgrade.sh' (ephemeral runners set TRUNK_INSTALL=1)." >&2
			exit 1
		fi
	fi
fi

DO_FMT=false
SYNC_ONLY=false
for arg in "$@"; do
	case "$arg" in
	--fmt)
		DO_FMT=true
		;;
	--sync-only)
		SYNC_ONLY=true
		;;
	-h | --help)
		echo "Usage: run-trunk-subrepos.sh [--fmt] [--sync-only]"
		exit 0
		;;
	esac
done

if [[ ${TRUNK_FMT:-0} == "1" ]]; then
	DO_FMT=true
fi

sync_trunk_defs() {
	local helper="${DIR}/scripts/sync-trunk-defs.mjs"
	if command -v node >/dev/null 2>&1 && [[ -f ${helper} ]]; then
		node "${helper}" "$@"
		return $?
	fi

	local shell_helper="${DIR}/.dev/automation/scripts/sync-trunk-configs.sh"
	if [[ -x ${shell_helper} ]]; then
		"${shell_helper}" "$@"
		return $?
	fi

	echo "Trunk sync helper missing; skipped." >&2
	return 1
}

if ! sync_trunk_defs --pull; then
	echo "Failed to sync Trunk definitions from canonical source." >&2
	exit 1
fi

if ! sync_trunk_defs --check; then
	echo "Trunk configuration drift detected after sync." >&2
	exit 1
fi

if [[ ${SYNC_ONLY} == true ]]; then
	echo "Trunk definitions synced; exiting due to --sync-only."
	exit 0
fi

mapfile -t REPOS < <(find . -maxdepth 3 -path "./*/.trunk/trunk.yaml" -not -path "./.trunk/trunk.yaml" -print | sed -e 's#^\./##' -e 's#/\.trunk/trunk\.yaml$##' | sort)
if [[ ${#REPOS[@]} -eq 0 ]]; then
	echo "No subrepositories with .trunk/trunk.yaml found; skipping trunk checks."
	exit 0
fi

ARTIFACTS_DIR="artifacts/trunk-results"
mkdir -p "${ARTIFACTS_DIR}"

FAILED=0
for repo in "${REPOS[@]}"; do
	if [[ -d ${repo} ]]; then
		printf "\n== Running trunk check in %s ==\n" "${repo}"
		pushd "${repo}" >/dev/null
		# Ensure git commands invoked by trunk can resolve submodule metadata even when run from temp dirs.
		LOCAL_GIT_DIR="${DIR}/.git/modules/${repo}"
		if [[ ! -d ${LOCAL_GIT_DIR} ]]; then
			LOCAL_GIT_DIR="$(pwd)/.git"
		fi
		export GIT_DIR="${LOCAL_GIT_DIR}"
		export GIT_WORK_TREE="$(pwd)"
		# Ensure subrepo trunk config exists
		if [[ -d ".trunk" ]]; then
			echo "Using local .trunk/trunk.yaml for ${repo}"
			if [[ ${DO_FMT} == true ]]; then
				"${TRUNK_BIN}" fmt || true
			fi
			"${TRUNK_BIN}" check --ci --no-progress --print-failures >"${DIR}/${ARTIFACTS_DIR}/${repo}.txt" || FAILED=1
		else
			echo "No .trunk found in ${repo}; running trunk check with default settings"
			if [[ ${DO_FMT} == true ]]; then
				"${TRUNK_BIN}" fmt || true
			fi
			"${TRUNK_BIN}" check --ci --no-progress --print-failures >"${DIR}/${ARTIFACTS_DIR}/${repo}.txt" || FAILED=1
		fi
		popd >/dev/null
	else
		echo "Skipping ${repo} (directory not present)"
	fi
done

if [[ ${FAILED} -ne 0 ]]; then
	echo "One or more trunk checks failed"
	python3 "${DIR}/.dev/automation/scripts/record-run-envelope.py" --capability workspace.trunkCheck --status failure --asset "${ARTIFACTS_DIR}" --notes "trunk check failures" || true
	exit 1
fi

echo "All trunk checks passed"
python3 "${DIR}/.dev/automation/scripts/record-run-envelope.py" --capability workspace.trunkCheck --status success --asset "${ARTIFACTS_DIR}" --notes "trunk checks passed" || true
exit 0
