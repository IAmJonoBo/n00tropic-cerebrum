#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
EXPORT_SCRIPT="$WORKSPACE_DIR/.dev/automation/scripts/erpnext-export.sh"
VERIFY_SCRIPT="$WORKSPACE_DIR/.dev/automation/scripts/erpnext-verify-checksums.sh"
DEFAULT_TELEMETRY_DIR="$WORKSPACE_DIR/12-Platform-Ops/telemetry"
LOG_DIR="${ERP_TELEMETRY_DIR:-$DEFAULT_TELEMETRY_DIR}"
LOG_FILE="$LOG_DIR/erpnext-automation.log"
DEFAULT_ENV_FILE="$WORKSPACE_DIR/12-Platform-Ops/secrets/erpnext.env"
ENV_FILE="${ERP_ENV_FILE:-$DEFAULT_ENV_FILE}"

mkdir -p "$LOG_DIR"

log() {
	local message="$1"
	printf '%s %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$message" | tee -a "$LOG_FILE" >&2
}

require_file() {
	local path="$1"
	local label="$2"
	if [[ ! -f $path ]]; then
		log "missing $label at $path"
		return 1
	fi
}

if [[ ! -x $EXPORT_SCRIPT || ! -x $VERIFY_SCRIPT ]]; then
	log "ensuring automation scripts are executable"
	chmod +x "$EXPORT_SCRIPT" "$VERIFY_SCRIPT"
fi

require_file "$ENV_FILE" "ERPNext environment" || {
	log "create the file using START HERE wizard or set ERP_ENV_FILE"
	exit 1
}

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

for var in ERP_API_BASE_URL ERP_API_KEY ERP_API_SECRET; do
	if [[ -z ${!var-} ]]; then
		log "variable $var is empty; aborting"
		exit 1
	fi
done

log "starting ERPNext export"
if ! EXPORT_OUTPUT=$(ERP_API_BASE_URL="$ERP_API_BASE_URL" ERP_API_KEY="$ERP_API_KEY" ERP_API_SECRET="$ERP_API_SECRET" bash "$EXPORT_SCRIPT" 2>>"$LOG_FILE"); then
	log "export script failed"
	exit 1
fi
printf '%s\n' "$EXPORT_OUTPUT" | tee -a "$LOG_FILE"

log "running checksum verification"
if ! VERIFY_OUTPUT=$(bash "$VERIFY_SCRIPT" 2>>"$LOG_FILE"); then
	log "checksum verification failed"
	exit 1
fi
printf '%s\n' "$VERIFY_OUTPUT" | tee -a "$LOG_FILE"

log "erpnext automation complete"
