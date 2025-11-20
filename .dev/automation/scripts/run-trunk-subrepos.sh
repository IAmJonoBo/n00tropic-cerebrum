#!/usr/bin/env bash
set -euo pipefail
DIR=$(cd "$(dirname "$0")/../../.." && pwd)
TRUNK_BIN="${TRUNK_BIN:-${HOME}/.trunk/bin/trunk}"
echo "Using trunk binary at: ${TRUNK_BIN}"
export VALE_LOCAL=1
export VALE_CONFIG="${DIR}/.vale.local.ini"
echo "VALE_CONFIG=${VALE_CONFIG}"
cd "${DIR}"

if ! command -v pnpm >/dev/null 2>&1; then
	echo "pnpm not found on PATH. Run scripts/setup-pnpm.sh first." >&2
	exit 1
fi

# Resolve trunk binary if TRUNK_BIN path is not present
if [[ ! -x ${TRUNK_BIN} ]]; then
	if command -v trunk >/dev/null 2>&1; then
		TRUNK_BIN="$(command -v trunk)"
		echo "Resolved trunk binary via PATH: ${TRUNK_BIN}"
	else
		echo "Trunk binary missing at ${TRUNK_BIN} and not found on PATH." >&2
		echo "Install trunk CLI v1.25.0 (per .trunk/trunk.yaml) to ~/.trunk/bin/trunk or set TRUNK_BIN." >&2
		exit 1
	fi
fi

# Sync trunk defs from base to subrepos to ensure supported definitions are present
pnpm run trunk:sync-defs || true

REPOS=(
	"n00-cortex"
	"n00-frontiers"
	"n00t"
	"n00plicate"
	"n00-dashboard"
	"n00-school"
)

ARTIFACTS_DIR="artifacts/trunk-results"
mkdir -p "${ARTIFACTS_DIR}"

FAILED=0
DO_FMT=false
if [[ $1 == "--fmt" || $TRUNK_FMT == "1" ]]; then
	DO_FMT=true
fi
for repo in "${REPOS[@]}"; do
	if [[ -d ${repo} ]]; then
		printf "\n== Running trunk check in %s ==\n" "${repo}"
		pushd "${repo}" >/dev/null
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
	exit 1
fi

echo "All trunk checks passed"
exit 0
