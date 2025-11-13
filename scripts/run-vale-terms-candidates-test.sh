#!/usr/bin/env bash
set -euo pipefail

# Sample run to test apply-edits and whitelist modes using sample artifacts
ARTIFACTS_JSON="artifacts/vale-full-sample.json"

echo "Running dry-run (preview):"
node scripts/vale-terms-candidates.mjs --json "${ARTIFACTS_JSON}" --dry-run --threshold 1

echo "\nSimulating interactive apply (dry run):"
node scripts/vale-terms-candidates.mjs --json "${ARTIFACTS_JSON}" --apply-edits --dry-run --threshold 1 --interactive || true

# Use --yes to actually apply edits (creates .bak backups)
# echo "Applying edits to sample files:"
# node scripts/vale-terms-candidates.mjs --json "$ARTIFACTS_JSON" --apply-edits --threshold 1 --yes

# Use whitelist to preview append
# node scripts/vale-terms-candidates.mjs --json "$ARTIFACTS_JSON" --whitelist vocab --dry-run --threshold 1

# Apply whitelist to vocab
# node scripts/vale-terms-candidates.mjs --json "$ARTIFACTS_JSON" --whitelist vocab --threshold 1 --yes

echo "Done test run"
