#!/usr/bin/env bash
set -euo pipefail

# normalize-workspace-pnpm.sh
# Usage: normalize-workspace-pnpm.sh [--dirs "dir1 dir2 dir3"] [--dry-run] [--force]
# This script removes node_modules and .pnpm directories and reinstalls packages with the
# canonical pnpm version from n00-cortex/data/toolchain-manifest.json. It is intended
# to update generated template renders and example projects so PNPM metadata matches the
# canonical pnpm version used in the workspace.

PNPM_VERSION=""
DRY_RUN=0
FORCE=0
INSTALL_WORKSPACE=0
DIRS=()

show_help() {
	cat <<EOF
Usage: $0 [--dirs "dir1 dir2 ..."] [--dry-run] [--force]

--dirs   Space-separated list of directories to clean and reinstall. If omitted,
         a sensible set of candidate directories is used: n00-frontiers build/template-renders and scaffold examples, n00-cortex, n00t, n00plicate, packages/*
--dry-run  Print what would be done without deleting anything
--force    Always reinstall even if a node_modules/.pnpm is not present

EOF
}

# Read args
while [[ $# -gt 0 ]]; do
	case "$1" in
	--help | -h)
		show_help
		exit 0
		;;
	--dirs)
		shift
		# Read space-delimited list of directories safely
		read -r -a DIRS <<<"$1"
		;;
	--dry-run)
		DRY_RUN=1
		;;
	--force)
		FORCE=1
		;;
	--install-workspace)
		INSTALL_WORKSPACE=1
		;;
	*)
		echo "Unknown arg: $1" >&2
		show_help
		exit 1
		;;
	esac
	shift
done

# Find canonical PNPM version from n00-cortex
if [[ -f "n00-cortex/data/toolchain-manifest.json" ]]; then
	PNPM_VERSION=$(jq -r '.toolchains.pnpm.version' n00-cortex/data/toolchain-manifest.json)
fi
if [[ -z ${PNPM_VERSION} || ${PNPM_VERSION} == "null" ]]; then
	PNPM_VERSION="10.23.0"
fi

# Sanity check Node pin vs workspace .nvmrc so we don't reinstall with mismatched runtime
if [[ -f .nvmrc ]]; then
	NVMRC=$(cat .nvmrc)
	MANIFEST_NODE=$(jq -r '.toolchains.node.version' n00-cortex/data/toolchain-manifest.json 2>/dev/null || true)
	if [[ -n ${MANIFEST_NODE} && ${MANIFEST_NODE} != "null" && ${NVMRC} != ${MANIFEST_NODE} ]]; then
		echo "[normalize-workspace-pnpm] warning: .nvmrc=${NVMRC} differs from manifest node=${MANIFEST_NODE}" >&2
	fi
fi

echo "Using PNPM_VERSION=${PNPM_VERSION}"

# Default dirs if none provided
if [[ ${#DIRS[@]} -eq 0 ]]; then
	DIRS=(
		"n00-frontiers/applications/scaffolder/build/template-renders"
		"n00-frontiers/applications/scaffolder/examples"
		"n00-cortex"
		"n00t"
		"n00plicate"
		"packages"
		"n00tropic"
	)
fi

# Activate corepack / pnpm
ACTIVATE_CMD="corepack enable && corepack prepare pnpm@${PNPM_VERSION} --activate"
echo "Activating pnpm ${PNPM_VERSION} via corepack: ${ACTIVATE_CMD}"
if [[ ${DRY_RUN} -eq 0 ]]; then
	eval "${ACTIVATE_CMD}"
fi

# Helper to run in Python-safe directories for spaces
normalize_dir() {
	local dir="$1"
	if [[ ! -d ${dir} ]]; then
		echo "Skipping missing directory: ${dir}"
		return
	fi

	echo "Processing: ${dir}"

	pushd "${dir}" >/dev/null

	# Check for package.json; if not, just remove node_modules
	if [[ -f package.json || -f pnpm-workspace.yaml ]]; then
		if [[ -d node_modules || -d .pnpm || ${FORCE} -eq 1 ]]; then
			echo "  -> Cleaning node_modules and .pnpm from ${dir}"
			if [[ ${DRY_RUN} -eq 0 ]]; then
				rm -rf node_modules .pnpm
			fi
			echo "  -> Installing using pnpm@${PNPM_VERSION}"
			if [[ ${DRY_RUN} -eq 0 ]]; then
				# Prefer frozen lockfile, but fall back to non-frozen if it fails
				set +e
				pnpm install --frozen-lockfile
				local rc=$?
				set -e
				if [[ ${rc} -ne 0 ]]; then
					echo "  -> frozen lockfile install failed; retrying without frozen lockfile"
					pnpm install --no-frozen-lockfile
				fi
			fi
		else
			echo "  -> Nothing to clean (no node_modules or .pnpm found)"
		fi
	else
		# No package.json; remove node_modules/.pnpm only
		if [[ -d node_modules || -d .pnpm ]]; then
			echo "  -> Cleaning node_modules and .pnpm (no package.json found)"
			if [[ ${DRY_RUN} -eq 0 ]]; then
				rm -rf node_modules .pnpm
			fi
		else
			echo "  -> Nothing to clean (no node_modules/.pnpm)"
		fi
	fi

	popd >/dev/null
}

# Expand directories via globbing and call normalize
for base in "${DIRS[@]}"; do
	# If the base matches a directory containing subdirectories with package.json, find them
	if [[ -d ${base} ]]; then
		# Find all directories that contain a package.json, pnpm-lock.yaml, or pnpm-workspace.yaml
		# Use portable find compatible with macOS (BSD) - extract parent directories
		while IFS= read -r dir; do
			normalize_dir "$dir"
		done < <(find "$base" -maxdepth 3 -type f \( -name "package.json" -o -name "pnpm-lock.yaml" -o -name "pnpm-workspace.yaml" \) -print0 | xargs -0 -n1 dirname | sort -u)
	else
		# just try to normalize the single dir
		normalize_dir "$base"
	fi
done

if [[ ${INSTALL_WORKSPACE} -eq 1 ]]; then
	echo "Running workspace pnpm install (-w) to reduce symlink conflicts..."
	if [[ ${DRY_RUN} -eq 0 ]]; then
		pnpm -w install --no-frozen-lockfile
	fi
fi

echo "Normalization script run completed."

exit 0
