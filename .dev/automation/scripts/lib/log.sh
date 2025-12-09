#!/usr/bin/env bash
# Simple logging helpers for automation scripts.

log_ts() { date +"%Y-%m-%dT%H:%M:%S%z"; }

log_info() { echo "[INFO  $(log_ts)] $*"; }
log_warn() { echo "[WARN  $(log_ts)] $*" >&2; }
log_error() { echo "[ERROR $(log_ts)] $*" >&2; }

log_fail() {
	log_error "$*"
	exit 1
}
