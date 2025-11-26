#!/usr/bin/env bash
# Run Renovate in local dry-run mode to preview updates without touching GitHub.
# AGENT_HOOK: dependency-management
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
IMAGE="renovate/renovate:37.398.2"
LOG_LEVEL="${RENOVATE_LOG_LEVEL:-info}"

run_with_docker() {
	if ! command -v docker >/dev/null 2>&1; then
		return 1
	fi
	echo "[deps-renovate] Using Docker image ${IMAGE}"
	docker run --rm \
		-v "${ROOT_DIR}:/workspace" \
		-w /workspace \
		-e LOG_LEVEL="${LOG_LEVEL}" \
		-e RENOVATE_CONFIG_FILE="/workspace/renovate.json" \
		"${IMAGE}" \
		--platform=local \
		--local-dir=/workspace \
		--dry-run \
		--log-level="${LOG_LEVEL}"
}

run_with_pnpm() {
	if ! command -v pnpm >/dev/null 2>&1; then
		echo "[deps-renovate] pnpm not found; install pnpm or run with Docker." >&2
		exit 1
	fi
	echo "[deps-renovate] Running renovate via pnpm dlx"
	pnpm dlx renovate@37 \
		--platform=local \
		--local-dir="${ROOT_DIR}" \
		--config-file="${ROOT_DIR}/renovate.json" \
		--dry-run \
		--log-level="${LOG_LEVEL}"
}

if ! run_with_docker; then
	run_with_pnpm
fi
