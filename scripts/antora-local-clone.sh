#!/usr/bin/env bash
set -euo pipefail

# antora-local-clone.sh
# CLI: --depth <n> (git clone depth), --no-cleanup (keep temp dir), --token <PAT>, --components "csv"
SCRIPT_PARENT="$(dirname "${BASH_SOURCE[0]}")/.."
if ! ROOT_DIR="$(cd "${SCRIPT_PARENT}" && pwd)"; then
	echo "Unable to determine repository root"
	exit 1
fi
TMP_DIR="/tmp/antora-dev-$(whoami)-$(date +%s)"
DEPTH=1
KEEP=false
TOKEN=${GITHUB_TOKEN-}
UI_PATH=""
REMOTE_UI=""
COMPONENTS=(n00tropic-cerebrum n00-frontiers n00-cortex n00t)
USE_WORKSPACE=false
STUB_UI=false

usage() {
	cat <<EOF
Usage: $0 [--depth N] [--no-cleanup] [--token TOKEN] [--components "a,b,c"]

Options:
  --depth N        Set git clone depth (default: 1)
  --no-cleanup     Keep the cloned repositories in TMP_DIR for inspection
  --token TOKEN    Use this GitHub token for cloning private repos
  --components     Comma-separated list of components to clone
  --help           Show this help
  --ui             Path to a local ui-bundle.zip (copied to tmp dir)
  --remote-ui      URL to a remote ui-bundle.zip to download to tmp dir
  --stub-ui        Generate and use a default minimal UI bundle
  --use-workspace  Clone components from the current workspace instead of GitHub remotes
EOF
}

while [[ $# -gt 0 ]]; do
	case "$1" in
	--depth)
		DEPTH="$2"
		shift 2
		;;
	--no-cleanup)
		KEEP=true
		shift 1
		;;
	--token)
		TOKEN="$2"
		shift 2
		;;
	--components)
		IFS=',' read -r -a COMPONENTS <<<"$2"
		shift 2
		;;
	--ui)
		UI_PATH="$2"
		shift 2
		;;
	--remote-ui)
		REMOTE_UI="$2"
		shift 2
		;;
	--stub-ui)
		# Generate the default UI bundle if none found in workspace
		STUB_UI=true
		shift 1
		;;
	--use-workspace)
		USE_WORKSPACE=true
		shift 1
		;;
	--help)
		usage
		exit 0
		;;
	*)
		echo "Unknown option: $1"
		usage
		exit 1
		;;
	esac
done

mkdir -p "${TMP_DIR}"

echo "Preparing local Antora environment in ${TMP_DIR}"

clone_repo() {
	local repo="$1"
	local target="${TMP_DIR}/${repo}"
	# Map workspace folder names to GitHub remote repo names when they differ
	local remote_repo="$repo"
	if [[ ${repo} == "n00tropic-cerebrum" ]]; then
		remote_repo="n00tropic-cerebrum"
	fi
	if [[ ${USE_WORKSPACE} == true ]]; then
		local src
		if [[ ${repo} == "n00tropic-cerebrum" ]]; then
			src="${ROOT_DIR}"
		else
			src="${ROOT_DIR}/${repo}"
		fi
		if [[ ! -d ${src} ]]; then
			echo "Workspace repo ${src} not found; cannot clone locally"
			return 1
		fi
		echo "Cloning local workspace ${src} -> ${target}"
		git clone --local --no-hardlinks "${src}" "${target}"
	else
		local url="https://github.com/n00tropic/${remote_repo}.git"
		echo "Cloning ${url} -> ${target} (depth: ${DEPTH})"
		if [[ -n ${TOKEN} ]]; then
			url="https://x-access-token:${TOKEN}@github.com/n00tropic/${remote_repo}.git"
		fi
		git clone --depth "${DEPTH}" "${url}" "${target}"
	fi
}

for repo in "${COMPONENTS[@]}"; do
	clone_repo "${repo}"
done

# If a local UI bundle exists in the workspace, copy it for the local playbook
UI_PRESENT=false
mkdir -p "${TMP_DIR}/vendor/antora"
if [[ -n ${UI_PATH} ]] && [[ -f ${UI_PATH} ]]; then
	echo "Using UI bundle from --ui path: ${UI_PATH}"
	cp "${UI_PATH}" "${TMP_DIR}/vendor/antora/ui-bundle.zip"
	UI_PRESENT=true
elif [[ -n ${REMOTE_UI} ]]; then
	echo "Downloading remote UI bundle from ${REMOTE_UI}"
	if command -v curl >/dev/null 2>&1; then
		curl -fsSL "${REMOTE_UI}" -o "${TMP_DIR}/vendor/antora/ui-bundle.zip" || true
	elif command -v wget >/dev/null 2>&1; then
		wget -qO "${TMP_DIR}/vendor/antora/ui-bundle.zip" "${REMOTE_UI}" || true
	else
		echo "No curl or wget available to download remote UI bundle; skipping download."
	fi
	if [[ -f "${TMP_DIR}/vendor/antora/ui-bundle.zip" ]]; then
		UI_PRESENT=true
	fi
elif [[ -f "${ROOT_DIR}/vendor/antora/ui-bundle.zip" ]]; then
	echo "Copying workspace UI bundle into local tmp vendor dir"
	cp "${ROOT_DIR}/vendor/antora/ui-bundle.zip" "${TMP_DIR}/vendor/antora/ui-bundle.zip"
	UI_PRESENT=true
else
	if [[ ${STUB_UI} == true ]]; then
		echo "Creating fallback UI bundle..."
		bash "${ROOT_DIR}/scripts/create-default-ui-bundle.sh"
		if [[ -f "${ROOT_DIR}/vendor/antora/ui-bundle.zip" ]]; then
			cp "${ROOT_DIR}/vendor/antora/ui-bundle.zip" "${TMP_DIR}/vendor/antora/ui-bundle.zip"
			UI_PRESENT=true
		fi
	else
		echo "No UI bundle found in workspace, and no --ui or --remote-ui provided. Will build without a custom UI bundle (use --ui or --remote-ui to override)."
	fi
fi

cleanup() {
	local status=$?
	if [[ ${KEEP} == false ]]; then
		echo "Cleaning up ${TMP_DIR}"
		rm -rf "${TMP_DIR}"
	fi
	exit "${status}"
}
trap cleanup EXIT

# Generate local playbook
PLAYBOOK="${TMP_DIR}/antora-playbook.local.yml"
cat >"${PLAYBOOK}" <<EOF
site:
  title: n00 Docs (local)
  start_page: n00tropic-cerebrum::index.adoc
content:
  sources:
EOF

VALID_COMPONENTS=()
for repo in "${COMPONENTS[@]}"; do
	if [[ -f "${TMP_DIR}/${repo}/docs/antora.yml" ]] || [[ -f "${TMP_DIR}/${repo}/antora.yml" ]]; then
		VALID_COMPONENTS+=("${repo}")
		echo "    - url: ${TMP_DIR}/${repo}" >>"${PLAYBOOK}"
		echo "      start_paths: [ docs ]" >>"${PLAYBOOK}"
	else
		echo "Warning: component ${repo} does not contain docs/antora.yml or antora.yml - skipping from playbook"
	fi
done

if [[ ${#VALID_COMPONENTS[@]} -eq 0 ]]; then
	echo "No valid Antora components were found in cloned components. Aborting local build."
	exit 1
fi

if [[ ${UI_PRESENT} == true ]]; then
	cat >>"${PLAYBOOK}" <<EOF
ui:
  bundle:
    url: ./vendor/antora/ui-bundle.zip
EOF
fi
cat >>"${PLAYBOOK}" <<EOF
antora:
  extensions:
    - "@antora/lunr-extension"
asciidoc:
  attributes:
    page-pagination: ""
    sectanchors: ""
    icons: font
    source-highlighter: highlight.js
runtime:
  fetch: true
EOF

echo "Local playbook generated at ${PLAYBOOK}"
echo "Running Antora using local playbook..."
pnpm exec antora "${PLAYBOOK}" --stacktrace

echo "Site built in build/site"
