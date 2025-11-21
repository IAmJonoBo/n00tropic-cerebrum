#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
WORKING_ROOT="$WORKSPACE_DIR"
ARCHIVE_ROOT="$WORKING_ROOT/90-Archive/erpnext-exports"
MANIFEST_FILE="$ARCHIVE_ROOT/checksums.json"
DEFAULT_TELEMETRY_DIR="$WORKING_ROOT/12-Platform-Ops/telemetry"
TELEMETRY_DIR="${ERP_TELEMETRY_DIR:-$DEFAULT_TELEMETRY_DIR}"
TELEMETRY_FILE="$TELEMETRY_DIR/erpnext-export-checksums.json"

mkdir -p "$ARCHIVE_ROOT" "$TELEMETRY_DIR"

if [[ ! -d "$ARCHIVE_ROOT" ]]; then
  echo "Archive directory not found: $ARCHIVE_ROOT" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to verify export checksums" >&2
  exit 1
fi

SUMMARY=$(ARCHIVE_ROOT="$ARCHIVE_ROOT" MANIFEST_FILE="$MANIFEST_FILE" WORKING_ROOT="$WORKING_ROOT" TELEMETRY_FILE="$TELEMETRY_FILE" python3 <<'PY'
import datetime
import hashlib
import json
import os
from pathlib import Path

archive_root = Path(os.environ["ARCHIVE_ROOT"])
manifest_file = Path(os.environ["MANIFEST_FILE"])
working_root = Path(os.environ["WORKING_ROOT"])

existing = {}
if manifest_file.exists():
    with manifest_file.open("r", encoding="utf-8") as handle:
        existing = json.load(handle)

new_manifest = {}
for path in archive_root.rglob('*'):
    if path.is_file():
        rel = path.relative_to(archive_root).as_posix()
        hasher = hashlib.sha256()
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(8192), b''):
                hasher.update(chunk)
        new_manifest[rel] = hasher.hexdigest()

added = sorted(set(new_manifest) - set(existing))
removed = sorted(set(existing) - set(new_manifest))
modified = sorted(
    rel for rel, digest in new_manifest.items()
    if rel in existing and existing[rel] != digest
)

manifest_file.parent.mkdir(parents=True, exist_ok=True)
with manifest_file.open('w', encoding='utf-8') as handle:
    json.dump(new_manifest, handle, indent=2, sort_keys=True)

summary = {
  "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    "added": added,
    "removed": removed,
    "modified": modified,
  "fileCount": len(new_manifest),
  "manifestPath": manifest_file.relative_to(working_root).as_posix(),
  "alert": bool(removed or modified)
}

summary["status"] = "failure" if summary["alert"] else "success"
summary["telemetryPath"] = Path(os.environ["TELEMETRY_FILE"]).relative_to(working_root).as_posix()

print(json.dumps(summary, indent=2))
PY
)

echo "$SUMMARY" >"$TELEMETRY_FILE"

printf '%s\n' "$SUMMARY"

if [[ "$SUMMARY" == *'"alert": true'* ]]; then
  echo "Checksum drift detected; check $TELEMETRY_FILE" >&2
else
  echo "Checksums verified (no alert)" >&2
fi
