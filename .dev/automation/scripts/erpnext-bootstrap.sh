#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DEFAULT_STACK_DIR="$WORKSPACE_DIR/.dev/automation/artifacts/erpnext-stack"
DEFAULT_PROJECT_NAME="erpnext-dev"
DEFAULT_SITE_NAME="frontend"
DEFAULT_HTTP_PORT="8080"
DEFAULT_ERP_VERSION="v15.87.0"
DEFAULT_DB_PASSWORD="admin"
DEFAULT_ADMIN_PASSWORD="admin"
DEFAULT_TIMEOUT_SECONDS=600

STACK_DIR="$DEFAULT_STACK_DIR"
PROJECT_NAME="$DEFAULT_PROJECT_NAME"
SITE_NAME="$DEFAULT_SITE_NAME"
HTTP_PORT="$DEFAULT_HTTP_PORT"
ERP_VERSION="$DEFAULT_ERP_VERSION"
DB_ROOT_PASSWORD="$DEFAULT_DB_PASSWORD"
ADMIN_PASSWORD="$DEFAULT_ADMIN_PASSWORD"
TIMEOUT_SECONDS=$DEFAULT_TIMEOUT_SECONDS
PULL_IMAGES=true
SKIP_AUTH_CHECK=false
REFRESH_TEMPLATE=false

usage() {
	cat <<'USAGE'
Usage: erpnext-bootstrap.sh [options]

Options:
  --stack-dir PATH         Directory to store generated compose + env files.
  --project-name NAME      Docker Compose project name (default: erpnext-dev).
  --site NAME              ERPNext site name to create (default: frontend).
  --http-port PORT         Host HTTP port to expose for ERPNext (default: 8080).
  --erpnext-version TAG    ERPNext image tag (default: v15.87.0).
  --db-password VALUE      MariaDB root password (default: admin).
  --admin-password VALUE   Administrator password for ERPNext (default: admin).
  --timeout SECONDS        Seconds to wait for site creation (default: 600).
  --skip-auth-check        Skip HTTP authentication validation.
  --no-pull                Skip docker compose pull prior to launch.
  --refresh-template       Regenerate docker-compose template even if it exists.
  --help                   Show this help text and exit.

Environment:
  CAPABILITY_INPUT         Optional JSON payload with keys matching the options above
                           (stackDir, projectName, site, httpPort, erpnextVersion,
                            dbPassword, adminPassword, timeout, skipAuthCheck,
                            noPull, refreshTemplate).
USAGE
}

fail() {
	printf 'Error: %s\n' "$1" >&2
	exit 1
}

print_step() {
	printf '\n==> %s\n' "$1"
}

print_info() {
	printf '    %s\n' "$1"
}

sanitize_env_value() {
	local key="$1"
	local value="$2"
	if [[ $value == *$'\n'* || $value == *$'\r'* ]]; then
		fail "$key contains newline characters, which are not supported"
	fi
	if [[ $value == "" ]]; then
		fail "$key must not be empty"
	fi
	if [[ $value =~ ^[[:space:]] || $value =~ [[:space:]]$ ]]; then
		fail "$key must not contain leading or trailing whitespace"
	fi
	if [[ $value =~ [[:space:]] ]]; then
		fail "$key must not include whitespace characters"
	fi
	if [[ $value == \#* ]]; then
		fail "$key must not start with #"
	fi
}

parse_capability_input() {
	if [[ -z ${CAPABILITY_INPUT-} ]]; then
		return
	fi
	if ! command -v python3 >/dev/null 2>&1; then
		fail "python3 is required to parse CAPABILITY_INPUT"
	fi
	local kv_pairs
	if ! kv_pairs=$(
		python3 - <<'PY'
import json
import os
raw = os.environ.get('CAPABILITY_INPUT')
if not raw:
    raise SystemExit
config = json.loads(raw)
for key in (
    'stackDir',
    'projectName',
    'site',
    'httpPort',
    'erpnextVersion',
    'dbPassword',
    'adminPassword',
    'timeout',
    'skipAuthCheck',
    'noPull',
    'refreshTemplate',
):
    if key in config and config[key] is not None:
        print(f"{key}={config[key]}")
PY
	); then
		fail "Failed to parse CAPABILITY_INPUT as JSON"
	fi
	local entry key value
	while IFS='=' read -r entry; do
		[[ -z $entry ]] && continue
		key="${entry%%=*}"
		value="${entry#*=}"
		case "$key" in
		stackDir) STACK_DIR="$value" ;;
		projectName) PROJECT_NAME="$value" ;;
		site) SITE_NAME="$value" ;;
		httpPort) HTTP_PORT="$value" ;;
		erpnextVersion) ERP_VERSION="$value" ;;
		dbPassword) DB_ROOT_PASSWORD="$value" ;;
		adminPassword) ADMIN_PASSWORD="$value" ;;
		timeout) TIMEOUT_SECONDS="$value" ;;
		skipAuthCheck) [[ $value =~ ^(1|true|TRUE|yes|YES)$ ]] && SKIP_AUTH_CHECK=true ;;
		noPull) [[ $value =~ ^(1|true|TRUE|yes|YES)$ ]] && PULL_IMAGES=false ;;
		refreshTemplate) [[ $value =~ ^(1|true|TRUE|yes|YES)$ ]] && REFRESH_TEMPLATE=true ;;
		esac
	done <<<"$kv_pairs"
}

parse_cli_args() {
	while [[ $# -gt 0 ]]; do
		case "$1" in
		--stack-dir)
			STACK_DIR="$2"
			shift 2
			;;
		--project-name)
			PROJECT_NAME="$2"
			shift 2
			;;
		--site)
			SITE_NAME="$2"
			shift 2
			;;
		--http-port)
			HTTP_PORT="$2"
			shift 2
			;;
		--erpnext-version)
			ERP_VERSION="$2"
			shift 2
			;;
		--db-password)
			DB_ROOT_PASSWORD="$2"
			shift 2
			;;
		--admin-password)
			ADMIN_PASSWORD="$2"
			shift 2
			;;
		--timeout)
			TIMEOUT_SECONDS="$2"
			shift 2
			;;
		--skip-auth-check)
			SKIP_AUTH_CHECK=true
			shift
			;;
		--no-pull)
			PULL_IMAGES=false
			shift
			;;
		--refresh-template)
			REFRESH_TEMPLATE=true
			shift
			;;
		--help | -h)
			usage
			exit 0
			;;
		*)
			fail "Unknown option: $1"
			;;
		esac
	done
}

ensure_prerequisites() {
	local deps=("docker" "curl" "python3")
	local missing=()
	for dep in "${deps[@]}"; do
		if ! command -v "$dep" >/dev/null 2>&1; then
			missing+=("$dep")
		fi
	done
	if ((${#missing[@]})); then
		fail "Missing required tools: ${missing[*]}"
	fi
	if ! docker info >/dev/null 2>&1; then
		fail "Docker daemon is not available"
	fi
	if ! docker compose version >/dev/null 2>&1; then
		fail "docker compose plugin not available"
	fi
}

prepare_stack_dir() {
	mkdir -p "$STACK_DIR"
	local gitignore="$STACK_DIR/.gitignore"
	if [[ ! -f $gitignore ]]; then
		cat >"$gitignore" <<'EOF'
*
!.gitignore
EOF
	fi
}

compose_file_path() {
	printf '%s' "$STACK_DIR/docker-compose.yml"
}

env_file_path() {
	printf '%s' "$STACK_DIR/stack.env"
}

write_compose_file() {
	local compose_file
	compose_file="$(compose_file_path)"
	if [[ -f $compose_file && $REFRESH_TEMPLATE == false ]]; then
		return
	fi
	cat >"$compose_file" <<'EOF'
version: "3"

services:
  backend:
    image: ${ERP_IMAGE}
    networks:
      - frappe_network
    deploy:
      restart_policy:
        condition: on-failure
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - logs:/home/frappe/frappe-bench/logs
    environment:
      DB_HOST: db
      DB_PORT: "3306"
      MYSQL_ROOT_PASSWORD: "${DB_ROOT_PASSWORD}"
      MARIADB_ROOT_PASSWORD: "${DB_ROOT_PASSWORD}"

  configurator:
    image: ${ERP_IMAGE}
    networks:
      - frappe_network
    deploy:
      restart_policy:
        condition: none
    entrypoint:
      - bash
      - -c
    command:
      - >
        ls -1 apps > sites/apps.txt;
        bench set-config -g db_host $$DB_HOST;
        bench set-config -gp db_port $$DB_PORT;
        bench set-config -g redis_cache "redis://$$REDIS_CACHE";
        bench set-config -g redis_queue "redis://$$REDIS_QUEUE";
        bench set-config -g redis_socketio "redis://$$REDIS_QUEUE";
        bench set-config -gp socketio_port $$SOCKETIO_PORT;
    environment:
      DB_HOST: db
      DB_PORT: "3306"
      REDIS_CACHE: redis-cache:6379
      REDIS_QUEUE: redis-queue:6379
      SOCKETIO_PORT: "9000"
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - logs:/home/frappe/frappe-bench/logs

  create-site:
    image: ${ERP_IMAGE}
    networks:
      - frappe_network
    deploy:
      restart_policy:
        condition: none
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - logs:/home/frappe/frappe-bench/logs
    entrypoint:
      - bash
      - -c
    command:
      - >
        wait-for-it -t 120 db:3306;
        wait-for-it -t 120 redis-cache:6379;
        wait-for-it -t 120 redis-queue:6379;
        export start=`date +%s`;
        until [[ -n `grep -hs ^ sites/common_site_config.json | jq -r ".db_host // empty"` ]] && \
          [[ -n `grep -hs ^ sites/common_site_config.json | jq -r ".redis_cache // empty"` ]] && \
          [[ -n `grep -hs ^ sites/common_site_config.json | jq -r ".redis_queue // empty"` ]];
        do
          echo "Waiting for sites/common_site_config.json to be created";
          sleep 5;
          if (( `date +%s`-start > 180 )); then
            echo "could not find sites/common_site_config.json with required keys";
            exit 1
          fi
        done;
        echo "sites/common_site_config.json found";
        bench new-site --mariadb-user-host-login-scope='%' --admin-password=${ADMIN_PASSWORD} --db-root-username=root --db-root-password=${DB_ROOT_PASSWORD} --install-app erpnext --set-default ${SITE_NAME};

  db:
    image: ${DB_IMAGE}
    networks:
      - frappe_network
    healthcheck:
      test: mysqladmin ping -h localhost --password=${DB_ROOT_PASSWORD}
      interval: 1s
      retries: 20
    deploy:
      restart_policy:
        condition: on-failure
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
      - --skip-character-set-client-handshake
      - --skip-innodb-read-only-compressed
    environment:
      MYSQL_ROOT_PASSWORD: "${DB_ROOT_PASSWORD}"
      MARIADB_ROOT_PASSWORD: "${DB_ROOT_PASSWORD}"
    volumes:
      - db-data:/var/lib/mysql

  frontend:
    image: ${ERP_IMAGE}
    networks:
      - frappe_network
    depends_on:
      - websocket
    deploy:
      restart_policy:
        condition: on-failure
    command:
      - nginx-entrypoint.sh
    environment:
      BACKEND: backend:8000
      FRAPPE_SITE_NAME_HEADER: ${SITE_NAME}
      SOCKETIO: websocket:9000
      UPSTREAM_REAL_IP_ADDRESS: 127.0.0.1
      UPSTREAM_REAL_IP_HEADER: X-Forwarded-For
      UPSTREAM_REAL_IP_RECURSIVE: "off"
      PROXY_READ_TIMEOUT: 120
      CLIENT_MAX_BODY_SIZE: 50m
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - logs:/home/frappe/frappe-bench/logs
    ports:
      - "${HTTP_PORT}:8080"

  queue-long:
    image: ${ERP_IMAGE}
    networks:
      - frappe_network
    deploy:
      restart_policy:
        condition: on-failure
    command:
      - bench
      - worker
      - --queue
      - long,default,short
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - logs:/home/frappe/frappe-bench/logs
    environment:
      FRAPPE_REDIS_CACHE: redis://redis-cache:6379
      FRAPPE_REDIS_QUEUE: redis://redis-queue:6379

  queue-short:
    image: ${ERP_IMAGE}
    networks:
      - frappe_network
    deploy:
      restart_policy:
        condition: on-failure
    command:
      - bench
      - worker
      - --queue
      - short,default
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - logs:/home/frappe/frappe-bench/logs
    environment:
      FRAPPE_REDIS_CACHE: redis://redis-cache:6379
      FRAPPE_REDIS_QUEUE: redis://redis-queue:6379

  redis-queue:
    image: ${REDIS_IMAGE}
    networks:
      - frappe_network
    deploy:
      restart_policy:
        condition: on-failure
    volumes:
      - redis-queue-data:/data

  redis-cache:
    image: ${REDIS_IMAGE}
    networks:
      - frappe_network
    deploy:
      restart_policy:
        condition: on-failure

  scheduler:
    image: ${ERP_IMAGE}
    networks:
      - frappe_network
    deploy:
      restart_policy:
        condition: on-failure
    command:
      - bench
      - schedule
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - logs:/home/frappe/frappe-bench/logs

  websocket:
    image: ${ERP_IMAGE}
    networks:
      - frappe_network
    deploy:
      restart_policy:
        condition: on-failure
    command:
      - node
      - /home/frappe/frappe-bench/apps/frappe/socketio.js
    environment:
      FRAPPE_REDIS_CACHE: redis://redis-cache:6379
      FRAPPE_REDIS_QUEUE: redis://redis-queue:6379
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - logs:/home/frappe/frappe-bench/logs

volumes:
  db-data:
  redis-queue-data:
  sites:
  logs:

networks:
  frappe_network:
    driver: bridge
EOF
}

write_env_file() {
	local env_file
	env_file="$(env_file_path)"
	sanitize_env_value "HTTP_PORT" "$HTTP_PORT"
	sanitize_env_value "SITE_NAME" "$SITE_NAME"
	sanitize_env_value "ERP_VERSION" "$ERP_VERSION"
	sanitize_env_value "DB_ROOT_PASSWORD" "$DB_ROOT_PASSWORD"
	sanitize_env_value "ADMIN_PASSWORD" "$ADMIN_PASSWORD"
	sanitize_env_value "PROJECT_NAME" "$PROJECT_NAME"
	cat >"$env_file" <<EOF
ERP_IMAGE=frappe/erpnext:${ERP_VERSION}
DB_IMAGE=mariadb:10.6
REDIS_IMAGE=redis:6.2-alpine
DB_ROOT_PASSWORD=${DB_ROOT_PASSWORD}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
SITE_NAME=${SITE_NAME}
HTTP_PORT=${HTTP_PORT}
EOF
}

compose_cmd() {
	local compose_file env_file
	compose_file="$(compose_file_path)"
	env_file="$(env_file_path)"
	docker compose --project-name "$PROJECT_NAME" --env-file "$env_file" -f "$compose_file" "$@"
}

urlencode() {
	python3 - "${1}" <<'PY'
import sys
import urllib.parse
print(urllib.parse.quote(sys.argv[1], safe=''))
PY
}

wait_for_site_creation() {
	local compose_file container_id status exit_code start now
	compose_file="$(compose_file_path)"
	start=$(date +%s)
	while true; do
		container_id=$(compose_cmd ps -q create-site || true)
		if [[ -z $container_id ]]; then
			if (($(date +%s) - start > TIMEOUT_SECONDS)); then
				return 1
			fi
			sleep 5
			continue
		fi
		status=$(docker inspect -f '{{.State.Status}}' "$container_id")
		if [[ $status == "exited" ]]; then
			exit_code=$(docker inspect -f '{{.State.ExitCode}}' "$container_id")
			if [[ $exit_code -eq 0 ]]; then
				return 0
			fi
			docker logs "$container_id" | tail -n 50 >&2 || true
			return 1
		fi
		if (($(date +%s) - start > TIMEOUT_SECONDS)); then
			docker logs "$container_id" | tail -n 50 >&2 || true
			return 1
		fi
		sleep 5
	done
}

validate_authentication() {
	if [[ $SKIP_AUTH_CHECK == true ]]; then
		print_info "Skipping HTTP authentication check (per flag)."
		return
	fi
	local login_url payload status tmp_file message
	login_url="http://127.0.0.1:${HTTP_PORT}/api/method/login"
	payload="usr=Administrator&pwd=$(urlencode "$ADMIN_PASSWORD")"
	tmp_file=$(mktemp)
	for attempt in {1..40}; do
		if status=$(curl -sS -o "$tmp_file" -w '%{http_code}' -X POST -H 'Content-Type: application/x-www-form-urlencoded' "$login_url" --data "$payload" 2>/dev/null); then
			if [[ $status == "200" ]]; then
				if grep -q 'Logged In' "$tmp_file"; then
					rm -f "$tmp_file"
					print_info "Authentication succeeded for Administrator."
					return
				fi
			fi
		fi
		sleep 5
	done
	printf '\nAuthentication response (last attempt):\n' >&2
	cat "$tmp_file" >&2 || true
	rm -f "$tmp_file"
	fail "Unable to authenticate Administrator via HTTP"
}

main() {
	parse_capability_input
	parse_cli_args "$@"
	ensure_prerequisites
	sanitize_env_value "HTTP_PORT" "$HTTP_PORT"
	sanitize_env_value "SITE_NAME" "$SITE_NAME"
	sanitize_env_value "ERP_VERSION" "$ERP_VERSION"
	sanitize_env_value "PROJECT_NAME" "$PROJECT_NAME"
	if [[ ! $HTTP_PORT =~ ^[0-9]+$ ]]; then
		fail "HTTP_PORT must be numeric"
	fi
	if [[ ! $TIMEOUT_SECONDS =~ ^[0-9]+$ ]]; then
		fail "timeout must be numeric"
	fi
	HTTP_PORT=$((10#$HTTP_PORT))
	TIMEOUT_SECONDS=$((10#$TIMEOUT_SECONDS))
	prepare_stack_dir
	write_compose_file
	write_env_file

	print_step "Launching ERPNext stack"
	if $PULL_IMAGES; then
		print_info "Pulling container images..."
		compose_cmd pull
	else
		print_info "Skipping image pull."
	fi

	compose_cmd up -d --remove-orphans
	print_info "Containers started. Awaiting site bootstrap..."

	if ! wait_for_site_creation; then
		fail "create-site job did not complete successfully"
	fi
	print_info "Site bootstrap completed."

	print_step "Validating Administrator login"
	validate_authentication

	print_step "ERPNext is ready"
	print_info "URL: http://127.0.0.1:${HTTP_PORT}"
	print_info "Username: Administrator"
	print_info "Password: (stored in $(env_file_path))"
	print_info "To stop the stack: docker compose --project-name ${PROJECT_NAME} --env-file $(env_file_path) -f $(compose_file_path) down"
}

main "$@"
