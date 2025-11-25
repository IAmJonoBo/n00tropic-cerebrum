#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SUBMODULE_JOBS=${SUBMODULE_JOBS:-8}
TOKEN=${GH_SUBMODULE_TOKEN:-${GITHUB_TOKEN-}}

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

log "Verifying superrepo layout"
"$ROOT_DIR/scripts/check-superrepo.sh"

log "Installing pnpm workspace dependencies"
pnpm install --frozen-lockfile

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
