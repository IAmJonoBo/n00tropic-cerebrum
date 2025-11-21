#!/bin/bash
# AI Workflow Utilities
# Common functions for error handling, logging, and fallbacks

set -euo pipefail

# Enhanced logging with emojis and timestamps
log_info() {
  echo "[ℹ️  $(date +%H:%M:%S)] $1"
}

log_success() {
  echo "[✅ $(date +%H:%M:%S)] $1"
}

log_warning() {
  echo "[⚠️  $(date +%H:%M:%S)] WARNING: $1" >&2
}

log_error() {
  echo "[❌ $(date +%H:%M:%S)] ERROR: $1" >&2
}

log_debug() {
  if [[ "${DEBUG:-false}" == "true" ]]; then
    echo "[🔍 $(date +%H:%M:%S)] DEBUG: $1" >&2
  fi
}

# Progress indicator
show_progress() {
  local step=$1
  local total=$2
  local desc=$3
  local percent=$(( step * 100 / total ))
  echo "[📊 $(date +%H:%M:%S)] Progress: $step/$total ($percent%) - $desc"
}

# Error handling with cleanup
error_exit() {
  local message=$1
  local cleanup_cmd=${2:-}

  log_error "$message"

  if [[ -n "$cleanup_cmd" ]]; then
    log_info "Running cleanup: $cleanup_cmd"
    eval "$cleanup_cmd" || log_warning "Cleanup failed"
  fi

  exit 1
}

# Check if command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Validate file exists and is readable
validate_file() {
  local file=$1
  local description=${2:-"file"}

  if [[ ! -f "$file" ]]; then
    error_exit "$description '$file' does not exist"
  fi

  if [[ ! -r "$file" ]]; then
    error_exit "$description '$file' is not readable"
  fi

  log_debug "$description '$file' validated"
}

# Validate directory exists and is writable
validate_directory() {
  local dir=$1
  local description=${2:-"directory"}

  if [[ ! -d "$dir" ]]; then
    log_info "Creating $description '$dir'"
    mkdir -p "$dir" || error_exit "Failed to create $description '$dir'"
  fi

  if [[ ! -w "$dir" ]]; then
    error_exit "$description '$dir' is not writable"
  fi

  log_debug "$description '$dir' validated"
}

# Safe input reading with defaults and validation
safe_read() {
  local prompt=$1
  local default=${2:-}
  local validation_func=${3:-}

  local input
  local full_prompt="$prompt"

  if [[ -n "$default" ]]; then
    full_prompt="$prompt (default: $default)"
  fi

  if [[ "${NON_INTERACTIVE:-false}" == "true" ]]; then
    if [[ -n "$default" ]]; then
      input="$default"
      log_info "Using default value: $input"
    else
      error_exit "Non-interactive mode requires default values for all inputs"
    fi
  else
    read -p "$full_prompt: " input || error_exit "Failed to read input"

    if [[ -z "$input" && -n "$default" ]]; then
      input="$default"
      log_info "Using default value: $input"
    fi
  fi

  # Run validation if provided
  if [[ -n "$validation_func" ]]; then
    if ! eval "$validation_func \"$input\""; then
      error_exit "Invalid input: $input"
    fi
  fi

  echo "$input"
}

# Validate email format
validate_email() {
  local email=$1
  [[ "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]
}

# Validate URL format
validate_url() {
  local url=$1
  [[ "$url" =~ ^https?:// ]]
}

# Check API key availability
check_api_key() {
  local service=$1
  local key_file=$2

  if [[ -f "$key_file" ]]; then
    log_success "$service API key found"
    return 0
  else
    log_warning "$service API key not found at $key_file"
    return 1
  fi
}

# Generate timestamp
timestamp() {
  date -u +"%Y%m%d-%H%M%S"
}

# Generate ISO timestamp
iso_timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# Backup file with timestamp
backup_file() {
  local file=$1
  local backup_dir=${2:-"."}

  if [[ -f "$file" ]]; then
    local backup_name="$(basename "$file").backup.$(timestamp)"
    local backup_path="$backup_dir/$backup_name"

    cp "$file" "$backup_path" || error_exit "Failed to backup $file"
    log_info "Backed up $file to $backup_path"
    echo "$backup_path"
  fi
}

# Check system dependencies
check_dependencies() {
  local deps=("$@")
  local missing=()

  for dep in "${deps[@]}"; do
    if ! command_exists "$dep"; then
      missing+=("$dep")
    fi
  done

  if [[ ${#missing[@]} -gt 0 ]]; then
    error_exit "Missing required dependencies: ${missing[*]}"
  fi

  log_debug "All dependencies satisfied: ${deps[*]}"
}

# Graceful fallback for API calls
api_call_with_fallback() {
  local api_command=$1
  local fallback_command=$2
  local description=${3:-"API call"}

  log_info "Attempting $description..."

  if eval "$api_command"; then
    log_success "$description succeeded"
    return 0
  else
    log_warning "$description failed, using fallback"
    if [[ -n "$fallback_command" ]]; then
      eval "$fallback_command" || error_exit "Both API call and fallback failed"
      return 0
    else
      error_exit "API call failed and no fallback provided"
    fi
  fi
}

# Export functions for use in other scripts
export -f log_info log_success log_warning log_error log_debug
export -f show_progress error_exit command_exists
export -f validate_file validate_directory safe_read
export -f validate_email validate_url check_api_key
export -f timestamp iso_timestamp backup_file
export -f check_dependencies api_call_with_fallback