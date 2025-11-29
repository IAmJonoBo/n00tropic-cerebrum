#!/usr/bin/env bash
set -euo pipefail

# Collect planner telemetry artifacts and surface them to n00-school for evaluation queues.

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
PLAN_DIR="$ROOT/.dev/automation/artifacts/plans"
SCHOOL_RUNS="$ROOT/n00-school/runs"
OUTPUT="$SCHOOL_RUNS/plan-telemetry-index.json"

# Ensure pinned Node version for any node-based downstream usage
# shellcheck source=/dev/null
source "$ROOT/scripts/ensure-nvm-node.sh" 2>/dev/null || true

mkdir -p "$PLAN_DIR" "$SCHOOL_RUNS"

mapfile -t plan_files < <(find "$PLAN_DIR" -type f -name 'horizons-*.json' -maxdepth 1 | sort)

if [[ ${#plan_files[@]} -eq 0 ]]; then
	echo "[planner-eval-sync] No plan artifacts found under $PLAN_DIR" >&2
	printf '{"status":"error","reason":"no_plan_artifacts","path":"%s"}\n' "$PLAN_DIR"
	exit 1
fi

latest_ts=$(date -Is)

{
	echo '{'
	echo '  "generated_at": '"\"$latest_ts\""','
	echo '  "plans": ['
	first=1
	for file in "${plan_files[@]}"; do
		[[ $first -eq 0 ]] && echo ','
		first=0
		rel=${file#"$ROOT/"}
		mtime=$(date -r "$file" -Is)
		echo '    {"path": '"\"$rel\""', "modified": '"\"$mtime\""'}'
	done
	echo '  ]'
	echo '}'
} >"$OUTPUT"

echo "[planner-eval-sync] Indexed ${#plan_files[@]} plans -> $OUTPUT"
printf '{"status":"ok","artifact":"%s","count":%d}\n' "$OUTPUT" "${#plan_files[@]}"
