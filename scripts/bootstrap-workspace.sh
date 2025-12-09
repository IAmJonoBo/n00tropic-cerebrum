#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SUBMODULE_JOBS=${SUBMODULE_JOBS:-8}
TOKEN=${GH_SUBMODULE_TOKEN:-${GITHUB_TOKEN-}}

# Ensure pinned Node version (nvm) for any Node-based steps
# shellcheck source=/dev/null
source "${ROOT_DIR}/scripts/ensure-nvm-node.sh" 2>/dev/null || true

log() { printf "[bootstrap-workspace] %s\n" "$*"; }

cd "$ROOT_DIR"

if [[ -n $TOKEN ]]; then
	log "Configuring authenticated submodule fetch"
	git -C "$ROOT_DIR" config --local "url.https://${TOKEN}:x-oauth-basic@github.com/.insteadOf" "https://github.com/" || true
else
	log "GH_SUBMODULE_TOKEN not set; relying on existing Git credentials"
fi

log "Syncing submodule metadata"
git -C "$ROOT_DIR" submodule sync --recursive
log "Updating submodules"
git -C "$ROOT_DIR" submodule update --init --recursive --jobs "$SUBMODULE_JOBS"

log "Enforcing skeleton and hooks"
python3 "$ROOT_DIR/.dev/automation/scripts/check-workspace-skeleton.py" --apply
bash "$ROOT_DIR/scripts/install-hooks.sh"
bash "$ROOT_DIR/scripts/tag-propagate.sh"

log "Linking subrepo .nvmrc files to workspace pin"
bash "$ROOT_DIR/.dev/automation/scripts/sync-nvmrc.sh"

log "Verifying superrepo layout"
"$ROOT_DIR/scripts/check-superrepo.sh"

log "Ensuring pnpm is available (corepack)"
bash "$ROOT_DIR/scripts/setup-pnpm.sh"

if [[ ${SKIP_BOOTSTRAP_TRUNK_UPGRADE:-0} == 1 ]]; then
	log "SKIP_BOOTSTRAP_TRUNK_UPGRADE=1; skipping workspace Trunk upgrade"
else
	log "Refreshing Trunk runtimes across the workspace"
	# Allow bootstrap to self-install the CLI so fresh environments do not hit Trunk drift warnings.
	BOOTSTRAP_TRUNK_FLAGS="${TRUNK_UPGRADE_FLAGS:-[\"--yes-to-all\",\"--ci\"]}"
	BOOTSTRAP_TRUNK_SMART="${TRUNK_UPGRADE_SMART:-1}"
	if TRUNK_INSTALL="${TRUNK_INSTALL:-1}" \
		TRUNK_INIT_MISSING="${TRUNK_INIT_MISSING:-0}" \
		TRUNK_UPGRADE_SMART="${BOOTSTRAP_TRUNK_SMART}" \
		TRUNK_UPGRADE_FLAGS="${BOOTSTRAP_TRUNK_FLAGS}" \
		python3 "$ROOT_DIR/cli.py" trunk-upgrade; then
		log "Trunk upgrade completed"
	else
		log "Trunk upgrade failed (non-blocking) – rerun 'python3 cli.py trunk-upgrade' once the environment is ready"
	fi
fi

if [[ ${ALLOW_ROOT_PNPM_INSTALL:-0} == 1 || ${CI-} == 1 ]]; then
	log "Installing pnpm workspace dependencies at root (ALLOW_ROOT_PNPM_INSTALL=${ALLOW_ROOT_PNPM_INSTALL:-0})"
	pnpm install --frozen-lockfile
else
	log "Skipping root pnpm install (guard-root-pnpm-install.mjs). Run per-repo installs or set ALLOW_ROOT_PNPM_INSTALL=1 if you understand the risk."
fi

log "Installing shared Python dependencies"
"$ROOT_DIR/scripts/bootstrap-python.sh"

if [[ -z ${SKIP_BOOTSTRAP_ANTORA-} ]]; then
	if [[ -d "$ROOT_DIR/docs/modules" ]]; then
		log "Building Antora site"
		if ! pnpm exec antora antora-playbook.yml --stacktrace; then
			log "Antora build failed (likely due to missing private sources). Re-run after submodules are accessible or set SKIP_BOOTSTRAP_ANTORA=1 to skip."
		fi
	else
		log "Docs module directory not found; skipping Antora build"
	fi
else
	log "SKIP_BOOTSTRAP_ANTORA set; skipping Antora build"
fi

log "Workspace bootstrap complete"
