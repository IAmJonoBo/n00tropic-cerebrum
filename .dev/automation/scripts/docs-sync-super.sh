#!/usr/bin/env bash
# Synchronize docs across the superproject and its docs submodules, then push updates.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

log() {
	printf '[docs-sync] %s\n' "$*"
}

GIT_USER_NAME="${GIT_USER_NAME:-docs-bot}"
GIT_USER_EMAIL="${GIT_USER_EMAIL:-docs-bot@n00tropic.dev}"

log "Configuring git user as ${GIT_USER_NAME} <${GIT_USER_EMAIL}>"
git config user.name "${GIT_USER_NAME}"
git config user.email "${GIT_USER_EMAIL}"

log "Fetching latest branches"
git fetch --all --prune

log "Checking out main"
git checkout main
git pull --ff-only origin main || true

log "Refreshing docs submodules"
git submodule update --init --recursive --remote n00-frontiers n00-cortex n00t || true

if command -v corepack >/dev/null 2>&1; then
	log "Enabling corepack and pinning pnpm 10.23.0"
	corepack enable || true
	corepack prepare pnpm@10.23.0 --activate || true
fi

log "Installing n00menon dependencies (frozen if possible)"
if ! pnpm -C n00menon install --frozen-lockfile; then
	pnpm -C n00menon install --no-frozen-lockfile
fi

log "Syncing n00menon doc surfaces"
pnpm -C n00menon run docs:sync

log "Building n00menon docs (typedoc)"
pnpm -C n00menon run docs:build

log "Validating n00menon docs sync state"
pnpm -C n00menon run docs:sync:check

log "Formatting workspace"
if command -v trunk >/dev/null 2>&1; then
	trunk fmt --all || true
else
	log "trunk not installed; skipping fmt"
fi

if git diff --quiet && git diff --cached --quiet; then
	log "No changes detected; exiting"
	exit 0
fi

log "Staging changes"
git add -A

log "Committing changes"
git commit -m "chore(docs): auto-sync docs surfaces"

log "Pushing to origin main and docs"
git push origin HEAD:main
git push origin HEAD:docs

log "Docs sync complete"
