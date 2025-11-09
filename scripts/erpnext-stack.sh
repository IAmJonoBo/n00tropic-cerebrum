#!/usr/bin/env bash
set -euo pipefail

# Single entrypoint for provisioning, updating, and running a local ERPNext stack.
# Requires: pnpm (via corepack), MariaDB, Redis, and python3.12+ available on PATH.

COMMAND=${1-}
STACK_ROOT=${STACK_ROOT:-"${HOME}/.local/share/erpnext-stack"}
BENCH_NAME=${BENCH_NAME:-"erpnext-bench"}
BENCH_PATH="${STACK_ROOT}/${BENCH_NAME}"
BENCH_VENV="${STACK_ROOT}/.bench-cli"
BENCH_BIN="${BENCH_VENV}/bin/bench"
HELPERS_BIN="${STACK_ROOT}/bin"

PYTHON_BIN=${ERP_PYTHON_BIN:-"python3.12"}
FRAPPE_BRANCH=${FRAPPE_BRANCH:-"version-15"}
ERPNEXT_BRANCH=${ERPNEXT_BRANCH:-"version-15"}
SITE_NAME=${ERP_SITE_NAME:-"erpnext.local"}
SITE_ADMIN_PASSWORD=${ERP_ADMIN_PASSWORD:-"admin"}
MARIADB_ROOT_PASSWORD=${ERP_DB_ROOT_PASSWORD:-"root"}

ensure_prereqs() {
	command -v pnpm >/dev/null 2>&1 || {
		echo "pnpm is required. Install it via corepack (corepack enable; corepack use pnpm@latest)." >&2
		exit 1
	}
	command -v "${PYTHON_BIN}" >/dev/null 2>&1 || {
		echo "Missing ${PYTHON_BIN}. Set ERP_PYTHON_BIN to a valid interpreter." >&2
		exit 1
	}
}

ensure_directories() {
	mkdir -p "${STACK_ROOT}" "${HELPERS_BIN}"
}

ensure_bench_cli() {
	if [[ ! -x ${BENCH_BIN} ]]; then
		"${PYTHON_BIN}" -m venv "${BENCH_VENV}"
		"${BENCH_VENV}/bin/pip" install --upgrade pip
		"${BENCH_VENV}/bin/pip" install frappe-bench==5.27.0
	fi
}

ensure_yarn_wrapper() {
	local wrapper="${HELPERS_BIN}/yarn"
	if [[ ! -x ${wrapper} ]]; then
		cat >"${wrapper}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

if ! command -v pnpm >/dev/null 2>&1; then
	echo "pnpm is required for this Yarn shim." >&2
	exit 1
fi

case "${1:-}" in
	install)
		shift || true
		args=()
				extra_flags=("--shamefully-hoist")
				for arg in "$@"; do
			case "${arg}" in
				--production)
					args+=("--prod")
					;;
				--check-files)
					;;
				*)
					args+=("${arg}")
					;;
			esac
		done
				exec pnpm install "${extra_flags[@]}" "${args[@]}"
		;;
	run)
		shift || true
				if [[ ${#} -eq 0 ]]; then
					exec pnpm run
				fi
				cmd=$1
				shift || true
				exec pnpm run "${cmd}" -- "$@"
		;;
	*)
		if [[ ${#} -eq 0 ]]; then
			exec pnpm
		fi
		case "$1" in
			-*)
				exec pnpm "$@"
				;;
			cache|config)
				exec pnpm "$@"
				;;
			*)
				cmd=$1
				shift || true
						exec pnpm run "${cmd}" -- "$@"
				;;
		esac
		;;
esac
EOF
		chmod +x "${wrapper}"
	fi
}

bench_env() {
	export PATH="${HELPERS_BIN}:${BENCH_VENV}/bin:${PATH}"
	export BENCH_PYTHON="${PYTHON_BIN}"
}

bench_cmd() {
	bench_env
	(cd "${BENCH_PATH}" && "${BENCH_BIN}" "$@")
}

setup_stack() {
	ensure_directories
	bench_env

	if [[ ! -d ${BENCH_PATH} ]]; then
		local legacy_candidates=("${PWD}/${BENCH_NAME}" "${HOME}/${BENCH_NAME}")
		for candidate in "${legacy_candidates[@]}"; do
			if [[ -d ${candidate} && ${candidate} != "${BENCH_PATH}" ]]; then
				local backup="${candidate}.bak-$(date +%Y%m%d%H%M%S)"
				echo "Found existing bench at ${candidate}; moving to ${backup} before reinitialising." >&2
				mv "${candidate}" "${backup}"
			fi
		done

		(
			cd "${STACK_ROOT}"
			"${BENCH_BIN}" init "${BENCH_NAME}" --frappe-branch "${FRAPPE_BRANCH}" --python "${PYTHON_BIN}" --skip-assets
		)
	fi

	if [[ ! -d ${BENCH_PATH} ]]; then
		echo "Bench initialisation failed: ${BENCH_PATH} not found." >&2
		exit 1
	fi

	if [[ ! -d "${BENCH_PATH}/apps/erpnext" ]]; then
		bench_cmd get-app --branch "${ERPNEXT_BRANCH}" erpnext https://github.com/frappe/erpnext.git
	fi

	if [[ ! -f "${BENCH_PATH}/sites/${SITE_NAME}/site_config.json" ]]; then
		bench_cmd new-site "${SITE_NAME}" --admin-password "${SITE_ADMIN_PASSWORD}" --mariadb-root-password "${MARIADB_ROOT_PASSWORD}"
	fi

	if ! grep -q '^erpnext$' "${BENCH_PATH}/sites/apps.txt" 2>/dev/null; then
		bench_cmd --site "${SITE_NAME}" install-app erpnext
	fi

	bench_cmd build
}

assert_stack_exists() {
	if [[ ! -d ${BENCH_PATH} ]]; then
		echo "Bench directory ${BENCH_PATH} not found. Run '${0##*/} setup' first." >&2
		exit 1
	fi
}

repos_need_update() {
	local repo_path=$1
	local branch=$2
	if [[ ! -d "${repo_path}/.git" ]]; then
		return 1
	fi
	if ! git -C "${repo_path}" fetch --quiet origin "${branch}"; then
		echo "Warning: unable to fetch updates for ${repo_path}. Skipping upgrade check." >&2
		return 1
	fi
	local behind
	behind=$(git -C "${repo_path}" rev-list --count "HEAD..origin/${branch}" || echo 0)
	[[ ${behind} -gt 0 ]]
}

maybe_upgrade() {
	local needs=0
	if repos_need_update "${BENCH_PATH}/apps/frappe" "${FRAPPE_BRANCH}"; then
		needs=1
	fi
	if repos_need_update "${BENCH_PATH}/apps/erpnext" "${ERPNEXT_BRANCH}"; then
		needs=1
	fi
	if [[ ${needs} -eq 1 ]]; then
		echo "Upstream updates detected; running bench update." >&2
		bench_cmd update --reset --patch
	fi
}

start_stack() {
	bench_env
	cd "${BENCH_PATH}"
	"${BENCH_BIN}" start &
	local bench_pid=$!
	BENCH_CHILD_PID=${bench_pid}
	trap 'echo "Stopping ERPNext services"; kill -TERM ${BENCH_CHILD_PID} >/dev/null 2>&1 || true; wait ${BENCH_CHILD_PID} >/dev/null 2>&1 || true' INT TERM
	trap 'kill -TERM ${BENCH_CHILD_PID} >/dev/null 2>&1 || true; wait ${BENCH_CHILD_PID} >/dev/null 2>&1 || true' EXIT
	wait ${bench_pid}
	trap - INT TERM EXIT
	unset BENCH_CHILD_PID
}

stop_stack() {
	bench_env
	pkill -f "honcho start" >/dev/null 2>&1 || true
	pkill -f "frappe.utils.scheduler" >/dev/null 2>&1 || true
	pkill -f "node .*frappe" >/dev/null 2>&1 || true
	echo "Requested ERPNext processes to terminate."
}

status_stack() {
	pgrep -f "frappe" >/dev/null 2>&1 && echo "ERPNext processes running" || echo "ERPNext not running"
}

usage() {
	cat <<EOF
Usage: ${0##*/} <command>

Commands:
  setup       Provision bench, clone apps, create site, and build assets (pnpm-backed).
  update      Fetch upstream changes and apply bench update when new commits exist.
  start       Launch bench start with pnpm shim; stops automatically on exit.
  run         Idempotent setup (if needed) followed by a managed start session.
  stop        Attempt to terminate lingering ERPNext processes.
  status      Quick running-state check via pgrep.
EOF
}

case "${COMMAND}" in
setup)
	ensure_prereqs
	ensure_directories
	ensure_bench_cli
	ensure_yarn_wrapper
	setup_stack
	;;
update)
	ensure_prereqs
	ensure_directories
	ensure_bench_cli
	ensure_yarn_wrapper
	assert_stack_exists
	maybe_upgrade
	;;
start)
	ensure_prereqs
	ensure_directories
	ensure_bench_cli
	ensure_yarn_wrapper
	assert_stack_exists
	maybe_upgrade
	start_stack
	;;
run)
	ensure_prereqs
	ensure_directories
	ensure_bench_cli
	ensure_yarn_wrapper
	setup_stack
	start_stack
	;;
stop)
	assert_stack_exists
	stop_stack
	;;
status)
	status_stack
	;;
*)
	usage
	exit 1
	;;
esac
