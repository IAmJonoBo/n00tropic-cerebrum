#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
WORKING_ROOT="$WORKSPACE_DIR"
ARCHIVE_ROOT="$WORKING_ROOT/90-Archive/erpnext-exports"
DEFAULT_TELEMETRY_DIR="$WORKING_ROOT/12-Platform-Ops/telemetry"
TELEMETRY_DIR="${ERP_TELEMETRY_DIR:-$DEFAULT_TELEMETRY_DIR}"
NOW_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
STAMP="$(date -u +"%Y-%m-%d")"

MODULES="accounting,crm,hr,projects,support"
FORMAT="json"
PAGE_LIMIT="500"

if [[ -n ${CAPABILITY_INPUT:-} ]]; then
  if command -v jq >/dev/null 2>&1; then
    parsed_modules=$(printf '%s' "$CAPABILITY_INPUT" | jq -r 'if has("modules") then (.modules | if type == "array" then map(tostring) | join(",") else tostring end) else empty end')
    parsed_format=$(printf '%s' "$CAPABILITY_INPUT" | jq -r 'if has("format") then .format else empty end')
    parsed_limit=$(printf '%s' "$CAPABILITY_INPUT" | jq -r 'if has("limit") then (.limit|tostring) else empty end')
    [[ -n $parsed_modules ]] && MODULES="$parsed_modules"
    [[ -n $parsed_format ]] && FORMAT="$parsed_format"
    [[ -n $parsed_limit ]] && PAGE_LIMIT="$parsed_limit"
  else
    echo "CAPABILITY_INPUT provided but jq is not installed; falling back to defaults" >&2
  fi
fi

usage() {
  cat <<USAGE
Usage: ${0##*/} [--modules accounting,crm] [--format json|csv] [--limit 500]

Environment variables:
  ERP_API_BASE_URL  ERPNext base URL (required)
  ERP_API_KEY       API key (required)
  ERP_API_SECRET    API secret (required)
USAGE
}

while [[ ${1-} ]]; do
  case "$1" in
    --modules)
      MODULES="$2"
      shift 2
      ;;
    --format)
      FORMAT="$2"
      shift 2
      ;;
    --limit)
      PAGE_LIMIT="$2"
      shift 2
      ;;
    -h|--help)
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

if [[ -z ${ERP_API_BASE_URL:-} || -z ${ERP_API_KEY:-} || -z ${ERP_API_SECRET:-} ]]; then
  echo "ERP_API_BASE_URL, ERP_API_KEY, and ERP_API_SECRET must be set" >&2
  exit 2
fi

mkdir -p "$ARCHIVE_ROOT" "$TELEMETRY_DIR"

IFS=',' read -r -a MODULE_ARRAY <<<"$MODULES"
mapfile -t MODULE_ARRAY < <(printf '%s\n' "${MODULE_ARRAY[@]}" | sed '/^$/d' | tr '[:upper:]' '[:lower:]' | sort -u)

declare -A module_endpoint=(
  [accounting]="api/method/erpnext.accounts.doctype.sales_invoice.sales_invoice.get_invoice_summary"
  [crm]="api/resource/Lead"
  [hr]="api/resource/Employee"
  [projects]="api/resource/Project"
  [support]="api/resource/Issue"
)

declare -A module_destination=(
  [accounting]="$WORKING_ROOT/05-Finance-Procurement/period-close"
  [crm]="$WORKING_ROOT/02-Revenue/exports"
  [hr]="$WORKING_ROOT/04-People/learning"
  [projects]="$WORKING_ROOT/03-Delivery/projects"
  [support]="$WORKING_ROOT/03-Delivery/support"
)

status_records=()
overall_status="success"

find_latest_export() {
  local module="$1"
  local latest=""

  if [[ -d "$ARCHIVE_ROOT/$module" ]]; then
    while IFS= read -r -d '' candidate; do
      if [[ -z "$latest" || "$candidate" -nt "$latest" ]]; then
        latest="$candidate"
      fi
    done < <(find "$ARCHIVE_ROOT/$module" -type f -name "${module}-*.${FORMAT}" ! -name "*${STAMP}*" -print0 2>/dev/null)
  fi

  printf '%s' "$latest"
}

create_placeholder_export() {
  local module="$1"
  local dest_path="$2"
  local archive_path="$3"
  local placeholder_name="${module}-${STAMP}-placeholder.${FORMAT}"
  local archive_file="$archive_path/$placeholder_name"

  if [[ "$FORMAT" == "csv" ]]; then
    cat <<EOF >"$archive_file"
module,status,message,timestamp
$module,placeholder,"ERPNext export unavailable; placeholder generated",$NOW_UTC
EOF
  else
    cat <<EOF >"$archive_file"
{
  "module": "$module",
  "status": "placeholder",
  "timestamp": "$NOW_UTC",
  "message": "ERPNext export unavailable; placeholder generated."
}
EOF
  fi

  cp "$archive_file" "$dest_path/$placeholder_name"
  printf 'placeholder|placeholder-generated'
}

attempt_fallback() {
  local module="$1"
  local dest_path="$2"
  local archive_path="$3"
  local latest_file

  latest_file="$(find_latest_export "$module")"

  if [[ -n "$latest_file" ]]; then
    local reuse_stamp
    reuse_stamp="$(basename "$latest_file" | sed -E 's/.*-([0-9]{4}-[0-9]{2}-[0-9]{2}).*/\1/')"
    local fallback_name="${module}-${STAMP}.${FORMAT}"
    cp "$latest_file" "$archive_path/$fallback_name"
    cp "$latest_file" "$dest_path/$fallback_name"
    printf 'fallback|reused-%s' "${reuse_stamp:-previous}"
    return 0
  fi

  create_placeholder_export "$module" "$dest_path" "$archive_path"
}

perform_export() {
  local module="$1"
  local endpoint="$2"
  local dest_root="$3"
  local archive_path="$ARCHIVE_ROOT/$module/$STAMP"
  local dest_path="$dest_root/$STAMP"
  local tmp_file
  local response_status="success"
  local notes=""

  mkdir -p "$archive_path" "$dest_path"

  if ! command -v curl >/dev/null 2>&1; then
    response_status="skipped"
    notes="curl-not-installed"
  else
    tmp_file="$(mktemp)"
    if [[ "$FORMAT" == "csv" ]]; then
      curl -fsSL -H "Authorization: token ${ERP_API_KEY}:${ERP_API_SECRET}" \
        -G "$ERP_API_BASE_URL/$endpoint" \
        --data-urlencode "limit_page_length=$PAGE_LIMIT" \
        --data-urlencode "doctype_format=CSV" \
        --data-urlencode "format=CSV" \
        --data-urlencode "delimiter=," \
        --output "$tmp_file" || {
          response_status="failure"
          notes="curl-error"
        }
    else
      curl -fsSL -H "Authorization: token ${ERP_API_KEY}:${ERP_API_SECRET}" \
        -G "$ERP_API_BASE_URL/$endpoint" \
        --data-urlencode "limit_page_length=$PAGE_LIMIT" \
        --output "$tmp_file" || {
          response_status="failure"
          notes="curl-error"
        }
    fi

    if [[ "$response_status" == "success" ]]; then
      local filename="${module}-${STAMP}.${FORMAT}"
      mv "$tmp_file" "$archive_path/$filename"
      cp "$archive_path/$filename" "$dest_path/$filename"
      notes="written"
    else
  rm -f "$tmp_file"
  local fallback_result
  fallback_result="$(attempt_fallback "$module" "$dest_path" "$archive_path" || true)"
      if [[ -n "$fallback_result" ]]; then
        response_status="${fallback_result%%|*}"
        notes="${fallback_result#*|}"
      fi
    fi
  fi

  status_records+=("${module}|${response_status}|${notes}")
}

for module in "${MODULE_ARRAY[@]}"; do
  endpoint="${module_endpoint[$module]:-}"
  dest="${module_destination[$module]:-}"

  if [[ -z "$endpoint" || -z "$dest" ]]; then
    status_records+=("${module}|skipped|unsupported")
    continue
  fi

  perform_export "$module" "$endpoint" "$dest"

done

details_json=""
for row in "${status_records[@]}"; do
  IFS='|' read -r module status notes <<<"$row"
  details_json+="{\"module\":\"$module\",\"status\":\"$status\",\"notes\":\"$notes\"},"
  if [[ "$status" == "failure" ]]; then
    overall_status="failure"
  elif [[ "$status" != "success" && "$overall_status" != "failure" ]]; then
    overall_status="partial"
  fi
done
details_json="[${details_json%,}]"

modules_json="["
for module in "${MODULE_ARRAY[@]}"; do
  modules_json+="\"$module\"," 
done
modules_json="${modules_json%,}]"

telemetry_path="$TELEMETRY_DIR/erpnext-export-${STAMP}.json"

cat >"$telemetry_path" <<JSON
{
  "timestamp": "$NOW_UTC",
  "format": "$FORMAT",
  "page_limit": "$PAGE_LIMIT",
  "modules": $modules_json,
  "details": $details_json,
  "status": "$overall_status",
  "telemetry_path": "$telemetry_path"
}
JSON

result_json=$(cat <<JSON
{
  "status": "$overall_status",
  "telemetryPath": "$telemetry_path",
  "timestamp": "$NOW_UTC",
  "format": "$FORMAT",
  "pageLimit": "$PAGE_LIMIT",
  "modules": $modules_json,
  "details": $details_json
}
JSON
)

printf '%s\n' "$result_json"

printf 'Exports complete: %s\n' "${status_records[*]}" >&2
