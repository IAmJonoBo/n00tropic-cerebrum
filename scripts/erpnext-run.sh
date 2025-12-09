#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
WORKSPACE_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)
STACK_SCRIPT="${SCRIPT_DIR}/erpnext-stack.sh"
JOBS_SCRIPT="${WORKSPACE_ROOT}/n00tropic/.dev/automation/tasks/run-erpnext-jobs.sh"

STACK_ROOT_DEFAULT="${HOME}/.local/share/erpnext-stack"
STACK_ROOT="${STACK_ROOT:-${STACK_ROOT_DEFAULT}}"
BENCH_NAME="${BENCH_NAME:-erpnext-bench}"
BENCH_PATH="${STACK_ROOT}/${BENCH_NAME}"
BENCH_LOG_DIR="${STACK_ROOT}/logs"
BENCH_LOG_FILE="${BENCH_LOG_DIR}/bench-start.log"
SITE_PORT="${ERP_SITE_PORT:-8000}"
SITE_PORT_CEILING="${ERP_SITE_PORT_MAX:-$((SITE_PORT + 50))}"
DEFAULT_HEALTH_PATH="/api/method/ping"
HEALTH_PATH="${ERP_HEALTH_PATH:-$DEFAULT_HEALTH_PATH}"
OPEN_BROWSER=1
RUN_JOBS=1
FORCE_SETUP=0
WAIT_TIMEOUT="${ERP_HEALTH_TIMEOUT:-180}"
SITE_URL_OVERRIDE="${ERP_SITE_URL-}"
ENV_FILE_OVERRIDE="${ERP_ENV_FILE-}"
EXIT_ON_TIMEOUT=1
BENCH_START_FLAGS="${BENCH_START_FLAGS:---no-dev}"
DEV_MODE=0
SKIP_BENCH_UPDATE="${SKIP_BENCH_UPDATE:-0}"
PROCFILE_OVERRIDE=""
ATTACH_ON_SUCCESS=0
HEALTH_CURL_OPTS=()

log() {
	printf '[erpnext-run] %s\n' "$*" >&2
}

# tag::snippet-erpnext-run[]
usage() {
	cat <<'EOF'
Usage: scripts/erpnext-run.sh [options]

Options:
  --no-browser        Skip auto-opening the ERPNext UI after startup.
  --skip-jobs         Do not run telemetry / PM export automation.
  --env-file <path>   Override the ERPNext API environment file used by jobs.
  --site-url <url>    Override the browser/health URL (default inferred from bench site).
  --health-path <uri> Override health endpoint path (default /api/method/ping).
  --timeout <seconds> Max time to wait for HTTP readiness (default 180).
  --force-setup       Re-run the full bench setup even if it already exists.
  --keep-alive-on-timeout  Leave bench running even when the health check fails.
  --dev-mode          Run bench with live reload/watchers (disables --no-dev flag).
  --skip-update       Skip checking/updating bench apps before start.
  --attach            Keep bench attached to this console (default detaches after success).
  -h, --help          Show this help.
Environment overrides:
  STACK_ROOT, BENCH_NAME, ERP_SITE_PORT, ERP_SITE_PORT_MAX, ERP_SITE_URL, ERP_ENV_FILE, ERP_HEALTH_TIMEOUT, ERP_HEALTH_PATH.
EOF
}
# end::snippet-erpnext-run[]

while [[ $# -gt 0 ]]; do
	case "$1" in
	--no-browser)
		OPEN_BROWSER=0
		shift
		;;
	--skip-jobs)
		RUN_JOBS=0
		shift
		;;
	--env-file)
		ENV_FILE_OVERRIDE="$2"
		shift 2
		;;
	--site-url)
		SITE_URL_OVERRIDE="$2"
		shift 2
		;;
	--health-path)
		HEALTH_PATH="$2"
		shift 2
		;;
	--timeout)
		WAIT_TIMEOUT="$2"
		shift 2
		;;
	--force-setup)
		FORCE_SETUP=1
		shift
		;;
	--keep-alive-on-timeout)
		EXIT_ON_TIMEOUT=0
		shift
		;;
	--dev-mode)
		DEV_MODE=1
		BENCH_START_FLAGS=""
		shift
		;;
	--skip-update)
		SKIP_BENCH_UPDATE=1
		shift
		;;
	--attach)
		ATTACH_ON_SUCCESS=1
		shift
		;;
	-h | --help)
		usage
		exit 0
		;;
	*)
		echo "Unknown option: $1" >&2
		usage
		exit 1
		;;
	esac
done

if [[ ! -x ${STACK_SCRIPT} ]]; then
	log "erpnext-stack.sh not found or not executable at ${STACK_SCRIPT}"
	exit 1
fi

detect_dir() {
	local first="$1"
	shift || true
	if [[ -d ${first} ]]; then
		printf '%s\n' "${first}"
		return
	fi
	for candidate in "$@"; do
		if [[ -d ${candidate} ]]; then
			printf '%s\n' "${candidate}"
			return
		fi
	done
	printf '%s\n' "${first}"
}

resolve_env_file() {
	if [[ -n ${ENV_FILE_OVERRIDE} ]]; then
		printf '%s\n' "${ENV_FILE_OVERRIDE}"
		return
	fi
	local candidates=(
		"${WORKSPACE_ROOT}/.secrets/erpnext/erpnext.env"
		"${WORKSPACE_ROOT}/.secrets/erpnext.env"
		"${WORKSPACE_ROOT}/n00tropic_HQ/12-Platform-Ops/secrets/erpnext.env"
		"${WORKSPACE_ROOT}/12-Platform-Ops/secrets/erpnext.env"
		"${WORKSPACE_ROOT}/n00tropic/12-Platform-Ops/secrets/erpnext.env"
		"${WORKSPACE_ROOT}/../n00tropic_HQ/12-Platform-Ops/secrets/erpnext.env"
	)
	for candidate in "${candidates[@]}"; do
		if [[ -f ${candidate} ]]; then
			printf '%s\n' "${candidate}"
			return
		fi
	done
	printf ''
}

TELEMETRY_DIR=$(detect_dir \
	"${WORKSPACE_ROOT}/n00tropic_HQ/12-Platform-Ops/telemetry" \
	"${WORKSPACE_ROOT}/12-Platform-Ops/telemetry" \
	"${WORKSPACE_ROOT}/artifacts/telemetry")
mkdir -p "${TELEMETRY_DIR}"
TELEMETRY_FILE="${TELEMETRY_DIR}/erpnext-runtime.json"

ENV_FILE=$(resolve_env_file)
if [[ -z ${ENV_FILE} ]]; then
	log "warning: ERPNext env file not found; run-erpnext-jobs will be skipped unless --env-file is provided"
	RUN_JOBS=0
else
	set -a
	# shellcheck disable=SC1090
	source "${ENV_FILE}"
	set +a
	log "Loaded ERPNext env vars from ${ENV_FILE}"
fi

run_stack_cmd() {
	local cmd="$1"
	shift || true
	local env_args=(
		"STACK_ROOT=${STACK_ROOT}"
		"BENCH_NAME=${BENCH_NAME}"
	)
	if [[ -n ${ERP_DB_ROOT_PASSWORD-} ]]; then
		env_args+=("ERP_DB_ROOT_PASSWORD=${ERP_DB_ROOT_PASSWORD}")
	fi
	if [[ -n ${ERP_ADMIN_PASSWORD-} ]]; then
		env_args+=("ERP_ADMIN_PASSWORD=${ERP_ADMIN_PASSWORD}")
	fi
	if [[ -n ${ERP_SITE_NAME-} ]]; then
		env_args+=("ERP_SITE_NAME=${ERP_SITE_NAME}")
	fi
	if [[ -n ${BENCH_START_FLAGS-} ]]; then
		env_args+=("BENCH_START_FLAGS=${BENCH_START_FLAGS}")
	fi
	env_args+=("SKIP_BENCH_UPDATE=${SKIP_BENCH_UPDATE}")
	env "${env_args[@]}" "${STACK_SCRIPT}" "${cmd}" "$@"
}

start_bench_process() {
	if [[ ${ATTACH_ON_SUCCESS} -eq 0 ]]; then
		mkdir -p "${BENCH_LOG_DIR}"
		: >"${BENCH_LOG_FILE}"
		log "Starting bench services via ${STACK_SCRIPT} (logging to ${BENCH_LOG_FILE})"
		run_stack_cmd start >>"${BENCH_LOG_FILE}" 2>&1 &
	else
		log "Starting bench services via ${STACK_SCRIPT}"
		run_stack_cmd start &
	fi
	STACK_PID=$!
}

host_resolves() {
	local host=$1
	[[ -z ${host} ]] && return 1
	python3 - "$host" <<'PY' >/dev/null 2>&1
import socket
import sys

host = sys.argv[1]
try:
	socket.getaddrinfo(host, None)
except socket.gaierror:
	sys.exit(1)
PY
}

parse_site_host_port() {
	python3 - "$1" <<'PY'
import sys
from urllib.parse import urlparse

parsed = urlparse(sys.argv[1])
host = parsed.hostname or ""
if parsed.port:
	port = parsed.port
else:
	port = 443 if parsed.scheme == "https" else 80
print(f"{host} {port}")
PY
}

bench_flags_include_procfile() {
	[[ ${BENCH_START_FLAGS-} =~ (^|[[:space:]])(-p|--procfile)([[:space:]]|$) ]]
}

prepare_procfile_override() {
	PROCFILE_OVERRIDE=""
	[[ ${DEV_MODE} -eq 1 ]] && return
	bench_flags_include_procfile && return
	if [[ ! -d ${BENCH_PATH} ]]; then
		return
	fi
	local procfile="${BENCH_PATH}/Procfile"
	if [[ ! -f ${procfile} ]]; then
		return
	fi
	local sanitized="${procfile}.no-watch"
	if [[ ! -f ${sanitized} || ${procfile} -nt ${sanitized} ]]; then
		log "Generating watcher-free Procfile at ${sanitized}"
		local tmpfile
		tmpfile=$(mktemp "${sanitized}.XXXXXX")
		awk '!match($0, /^[[:space:]]*watch:/)' "${procfile}" >"${tmpfile}"
		mv "${tmpfile}" "${sanitized}"
	fi
	PROCFILE_OVERRIDE="${sanitized}"
	if [[ -z ${BENCH_START_FLAGS} ]]; then
		BENCH_START_FLAGS="--procfile ${PROCFILE_OVERRIDE}"
	else
		BENCH_START_FLAGS="${BENCH_START_FLAGS} --procfile ${PROCFILE_OVERRIDE}"
	fi
	log "Watch process disabled (override: ${PROCFILE_OVERRIDE}). Re-run with --dev-mode to restore live reload."
}

ensure_process() {
	local pattern=$1
	local description=$2
	local found=0
	IFS=',' read -r -a names <<<"${pattern}"
	for name in "${names[@]}"; do
		name=${name// /}
		[[ -z ${name} ]] && continue
		if pgrep -x "${name}" >/dev/null 2>&1 || pgrep -f "${name}" >/dev/null 2>&1; then
			found=1
			break
		fi
	done
	if [[ ${found} -eq 1 ]]; then
		log "${description} detected"
	else
		log "warning: ${description} not running. Start it before continuing (e.g. 'brew services start ${pattern%%,*}')."
	fi
}

ensure_prereqs() {
	command -v mysql >/dev/null 2>&1 || log "warning: 'mysql' CLI not found; install MariaDB to avoid bench failures."
	command -v redis-server >/dev/null 2>&1 || log "warning: 'redis-server' not found; bench workers may fail."
	ensure_process "mariadbd,mysqld" "MariaDB server"
	ensure_process "redis-server" "Redis server"
}

bootstrap_bench() {
	if [[ ${FORCE_SETUP} -eq 1 || ! -d ${BENCH_PATH} ]]; then
		log "Bootstrapping ERPNext bench (this may take a few minutes)"
		run_stack_cmd setup
	else
		log "Bench already initialised at ${BENCH_PATH}"
	fi
}

detect_site_name() {
	if [[ -n ${ERP_SITE_NAME-} ]]; then
		printf '%s\n' "${ERP_SITE_NAME}"
		return
	fi
	local current_site_file="${BENCH_PATH}/sites/currentsite.txt"
	if [[ -f ${current_site_file} ]]; then
		local site
		site=$(tr -d '[:space:]' <"${current_site_file}")
		if [[ -n ${site} ]]; then
			printf '%s\n' "${site}"
			return
		fi
	fi
	local first_site
	if [[ -d "${BENCH_PATH}/sites" ]]; then
		local site_dir="${BENCH_PATH}/sites"
		shopt -s nullglob
		for site_path in "${site_dir}"/*; do
			local candidate
			candidate=$(basename "${site_path}")
			case "${candidate}" in
			assets | logs | .DS_Store)
				continue
				;;
			.*)
				continue
				;;
			*)
				first_site="${candidate}"
				break
				;;
			esac
		done
		shopt -u nullglob
	fi
	printf '%s\n' "${first_site:-erpnext.local}"
}

find_available_port() {
	local start="$1"
	local ceiling="$2"
	if [[ $ceiling -lt $start ]]; then
		ceiling="$start"
	fi
	python3 - "$start" "$ceiling" <<'PY'
import socket
import sys

start = int(sys.argv[1])
ceiling = int(sys.argv[2])
for port in range(start, ceiling + 1):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            continue
        print(port)
        sys.exit(0)
print(start)
sys.exit(1)
PY
}

determine_site_url() {
	if [[ -n ${SITE_URL_OVERRIDE} ]]; then
		printf '%s\n' "${SITE_URL_OVERRIDE}"
		return
	fi
	local site_name
	site_name=$(detect_site_name)
	printf 'http://%s:%s\n' "${site_name}" "${SITE_PORT}"
}

AVAILABLE_SITE_PORT=$(find_available_port "${SITE_PORT}" "${SITE_PORT_CEILING}")
if [[ ${AVAILABLE_SITE_PORT} != "${SITE_PORT}" ]]; then
	log "Port ${SITE_PORT} busy; shifting ERPNext site to ${AVAILABLE_SITE_PORT} (override via ERP_SITE_PORT*)."
	SITE_PORT="${AVAILABLE_SITE_PORT}"
fi

SITE_URL=$(determine_site_url)
SITE_HOST=""
SITE_PORT_VALUE="${SITE_PORT}"
if SITE_COMPONENTS=$(parse_site_host_port "${SITE_URL}" 2>/dev/null); then
	read -r parsed_host parsed_port <<<"${SITE_COMPONENTS}"
	if [[ -n ${parsed_host-} ]]; then
		SITE_HOST="${parsed_host}"
	fi
	if [[ -n ${parsed_port-} ]]; then
		SITE_PORT_VALUE="${parsed_port}"
	fi
fi
SITE_PORT="${SITE_PORT_VALUE}"

HEALTH_URL="${SITE_URL%/}${HEALTH_PATH}"
if [[ -n ${SITE_HOST} && ${SITE_HOST} != "localhost" && ${SITE_HOST} != "127.0.0.1" ]]; then
	if ! host_resolves "${SITE_HOST}"; then
		HEALTH_CURL_OPTS+=(--resolve "${SITE_HOST}:${SITE_PORT}:127.0.0.1")
		log "Host ${SITE_HOST} not resolvable locally; health checks will tunnel via 127.0.0.1."
	fi
fi

write_runtime_file() {
	local status=$1
	local message=$2
	cat >"${TELEMETRY_FILE}" <<EOF
{
  "status": "${status}",
  "message": "${message}",
  "siteUrl": "${SITE_URL}",
  "healthUrl": "${HEALTH_URL}",
  "stackRoot": "${STACK_ROOT}",
  "benchName": "${BENCH_NAME}",
  "benchPath": "${BENCH_PATH}",
  "startedAt": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
}

wait_for_health() {
	if ! command -v curl >/dev/null 2>&1; then
		log "curl not available; skipping HTTP health verification"
		return 0
	fi
	local waited=0
	local interval=5
	while [[ ${waited} -lt ${WAIT_TIMEOUT} ]]; do
		if [[ -n ${STACK_PID-} ]] && ! kill -0 "${STACK_PID}" >/dev/null 2>&1; then
			log "bench process exited while waiting for health"
			return 1
		fi
		local -a curl_cmd=(curl -fsS)
		if ((${#HEALTH_CURL_OPTS[@]})); then
			curl_cmd+=("${HEALTH_CURL_OPTS[@]}")
		fi
		curl_cmd+=("${HEALTH_URL}")
		if "${curl_cmd[@]}" >/dev/null 2>&1; then
			return 0
		fi
		sleep "${interval}"
		waited=$((waited + interval))
	done
	return 1
}

open_browser() {
	[[ ${OPEN_BROWSER} -eq 1 ]] || return 0
	local opener=""
	if command -v open >/dev/null 2>&1; then
		opener="open"
	elif command -v xdg-open >/dev/null 2>&1; then
		opener="xdg-open"
	fi
	if [[ -n ${opener} ]]; then
		"${opener}" "${SITE_URL}" >/dev/null 2>&1 || log "warning: failed to open browser via ${opener}"
	else
		log "browser opener not found; navigate to ${SITE_URL} manually"
	fi
}

run_jobs() {
	[[ ${RUN_JOBS} -eq 1 ]] || return 0
	if [[ ! -x ${JOBS_SCRIPT} ]]; then
		log "warning: telemetry job script missing at ${JOBS_SCRIPT}; skipping"
		return 0
	fi
	if [[ ! -f ${ENV_FILE} ]]; then
		log "warning: ERPNext env file not found; skipping telemetry jobs"
		return 0
	fi
	log "Running telemetry / PM export automation"
	if ! ERP_ENV_FILE="${ENV_FILE}" ERP_TELEMETRY_DIR="${TELEMETRY_DIR}" bash "${JOBS_SCRIPT}"; then
		log "warning: telemetry automation reported failures"
		return 1
	fi
}

ensure_prereqs
bootstrap_bench
prepare_procfile_override
run_stack_cmd stop >/dev/null 2>&1 || true

write_runtime_file "starting" "Launching bench stack"

STACK_PID=
cleanup() {
	if [[ -n ${STACK_PID-} ]]; then
		log "Stopping ERPNext stack (PID ${STACK_PID})"
		kill -TERM "${STACK_PID}" >/dev/null 2>&1 || true
		wait "${STACK_PID}" >/dev/null 2>&1 || true
	fi
}
trap cleanup EXIT INT TERM

detach_stack() {
	if [[ -z ${STACK_PID-} ]]; then
		return
	fi
	trap - EXIT INT TERM
	if kill -0 "${STACK_PID}" >/dev/null 2>&1; then
		disown "${STACK_PID}" >/dev/null 2>&1 || true
	fi
	STACK_PID=
}

start_bench_process

if wait_for_health; then
	log "ERPNext responding at ${SITE_URL}"
	open_browser
	run_jobs || true
	write_runtime_file "ready" "ERPNext responding at ${SITE_URL}"
	if [[ ${ATTACH_ON_SUCCESS} -eq 0 ]]; then
		if [[ -f ${BENCH_LOG_FILE} ]]; then
			log "Bench is running in the background. Tail logs with: tail -f ${BENCH_LOG_FILE}"
		else
			log "Bench is running in the background. Stop it later via ${STACK_SCRIPT} stop or re-run with --attach to follow logs."
		fi
		detach_stack
		exit 0
	fi
else
	log "warning: ERPNext did not pass health check within ${WAIT_TIMEOUT}s; leaving stack running for inspection"
	write_runtime_file "degraded" "Health check timed out after ${WAIT_TIMEOUT}s"
	if [[ ${EXIT_ON_TIMEOUT} -eq 1 ]]; then
		log "Health check timed out; stopping bench to avoid hanging session. Re-run with --keep-alive-on-timeout to keep it running."
		cleanup
		exit 1
	fi
	log "Timeout keep-alive requested; bench will continue running in the background. Stop it later via ${STACK_SCRIPT} stop."
	if [[ -f ${BENCH_LOG_FILE} ]]; then
		log "Inspect logs with: tail -f ${BENCH_LOG_FILE}"
	fi
	detach_stack
	exit 1
fi

if [[ -n ${STACK_PID-} ]]; then
	wait "${STACK_PID}"
	EXIT_CODE=$?
	STACK_PID=
	write_runtime_file "stopped" "Bench exited with status ${EXIT_CODE}"
	exit "${EXIT_CODE}"
fi

exit 0
