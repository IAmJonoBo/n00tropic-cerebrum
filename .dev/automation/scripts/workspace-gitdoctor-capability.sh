#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../../.." && pwd)
N00T_DIR="${ROOT_DIR}/n00t"

if [[ ! -d $N00T_DIR ]]; then
	echo "n00t submodule not found at $N00T_DIR" >&2
	exit 1
fi

if ! command -v pnpm >/dev/null 2>&1; then
	echo "pnpm is required to invoke workspace.gitDoctor. Install pnpm (or enable corepack) before running this helper." >&2
	exit 1
fi

SYNC=false
CLEAN=false
PUBLISH=false
STRICT=false
PLAN_ONLY=false
PROMPT_OVERRIDE=""
FORWARDED=()

while [[ $# -gt 0 ]]; do
	case "$1" in
	--sync-submodules)
		SYNC=true
		;;
	--clean-untracked)
		CLEAN=true
		;;
	--publish-artifact)
		PUBLISH=true
		;;
	--strict)
		STRICT=true
		;;
	--plan-only)
		PLAN_ONLY=true
		;;
	--prompt)
		if [[ $# -lt 2 ]]; then
			echo "--prompt requires a value" >&2
			exit 1
		fi
		PROMPT_OVERRIDE="$2"
		shift
		;;
	--)
		shift
		while [[ $# -gt 0 ]]; do
			FORWARDED+=("$1")
			shift
		done
		break
		;;
	*)
		FORWARDED+=("$1")
		;;
	esac
	shift || true
done

if [[ -n $PROMPT_OVERRIDE ]]; then
	PAYLOAD="$PROMPT_OVERRIDE"
else
	entries=()
	if [[ $SYNC == true ]]; then
		entries+=('"syncSubmodules":true')
	fi
	if [[ $CLEAN == true ]]; then
		entries+=('"cleanUntracked":true')
	fi
	if [[ $PUBLISH == true ]]; then
		entries+=('"publishArtifact":true')
	fi
	if [[ $STRICT == true ]]; then
		entries+=('"strict":true')
	fi
	if ((${#entries[@]} > 0)); then
		IFS=,
		PAYLOAD="{${entries[*]}}"
		unset IFS
	else
		PAYLOAD=""
	fi
fi

CMD=(pnpm --filter n00t-agent-runner start -- --auto-approve --capability workspace.gitDoctor)
if [[ -n $PAYLOAD ]]; then
	CMD+=(--prompt "$PAYLOAD")
fi
if [[ $PLAN_ONLY == true ]]; then
	CMD+=(--plan-only)
fi
CMD+=("${FORWARDED[@]}")

(
	cd "$N00T_DIR"
	"${CMD[@]}"
)
