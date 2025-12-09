#!/usr/bin/env bash
# Upgrade GitHub Actions self-hosted runner with backup/rollback safety.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
RUNNER_DIR="${ROOT}/actions-runner"
BACKUP_DIR="${ROOT}/actions-runner.bak-$(date -u +%Y%m%d%H%M%S)"
TMP_TARBALL="/tmp/actions-runner.tar.gz"

log() { printf '[runner-upgrade] %s\n' "$*"; }
fail() {
	log "ERROR: $*"
	exit 1
}

if [[ ! -d $RUNNER_DIR ]]; then
	fail "actions-runner directory not found at $RUNNER_DIR"
fi

OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS" in
Linux) platform="linux" ;;
Darwin) platform="osx" ;;
*) fail "Unsupported OS: $OS" ;;
esac
case "$ARCH" in
x86_64 | amd64) arch="x64" ;;
arm64 | aarch64) arch="arm64" ;;
*) fail "Unsupported arch: $ARCH" ;;
esac

log "Detecting latest runner release"
LATEST_TAG="$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest | jq -r '.tag_name')"
if [[ -z $LATEST_TAG || $LATEST_TAG == "null" ]]; then
	fail "Could not determine latest runner version"
fi
VERSION="${LATEST_TAG#v}"
TARBALL_NAME="actions-runner-${platform}-${arch}-${VERSION}.tar.gz"
DOWNLOAD_URL="https://github.com/actions/runner/releases/download/${LATEST_TAG}/${TARBALL_NAME}"
log "Latest: ${LATEST_TAG} (${TARBALL_NAME})"

log "Stopping service if present"
if [[ -x "${RUNNER_DIR}/svc.sh" ]]; then
	(cd "$RUNNER_DIR" && ./svc.sh stop) || true
fi

log "Backing up current runner to ${BACKUP_DIR}"
mv "$RUNNER_DIR" "$BACKUP_DIR"
mkdir -p "$RUNNER_DIR"

cleanup_on_fail() {
	log "Restoring backup..."
	rm -rf "$RUNNER_DIR"
	mv "$BACKUP_DIR" "$RUNNER_DIR"
}
trap 'cleanup_on_fail' ERR

log "Downloading ${DOWNLOAD_URL}"
curl -fsSL "$DOWNLOAD_URL" -o "$TMP_TARBALL"

log "Extracting tarball"
tar -xzf "$TMP_TARBALL" -C "$RUNNER_DIR"

log "Restoring credentials and config from backup if present"
for f in .runner .credentials .credentials_rsaparams .service .env .path; do
	if [[ -f "$BACKUP_DIR/$f" ]]; then
		cp "$BACKUP_DIR/$f" "$RUNNER_DIR/$f"
	fi
done

log "Version after upgrade:"
if [[ -x "${RUNNER_DIR}/bin/Runner.Listener" ]]; then
	"${RUNNER_DIR}/bin/Runner.Listener" --version || true
fi

log "If using a service, reinstall/start it:"
echo "  cd ${RUNNER_DIR} && sudo ./svc.sh install || true"
echo "  cd ${RUNNER_DIR} && sudo ./svc.sh start"

log "Upgrade complete. Backup kept at ${BACKUP_DIR}"
