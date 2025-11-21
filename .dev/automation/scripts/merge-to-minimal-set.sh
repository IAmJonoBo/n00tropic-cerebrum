#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

echo "[merge-to-minimal-set] Checking open PRs labeled 'automerge' to merge into main"

if ! command -v gh >/dev/null 2>&1; then
	echo "gh CLI not found. Install GitHub CLI to use this script."
	exit 1
fi

OWNER="$(git remote get-url origin | sed -E 's#.*github.com[:/]+([^/]+)/([^/]+).git#\1#' || true)"
REPO="$(git remote get-url origin | sed -E 's#.*github.com[:/]+([^/]+)/([^/]+).git#\2#' || true)"
echo "Repository detected: ${OWNER}/${REPO}"

PRS_TO_MERGE=$(gh pr list --label automerge --json number,mergeable -q '.[] | select(.mergeable == "MERGEABLE") | .number')
if [ -z "$PRS_TO_MERGE" ]; then
	echo "No automergeable PRs currently open"
	exit 0
fi

for PR_NUM in $PRS_TO_MERGE; do
	echo "Merging PR #${PR_NUM}"
	gh pr merge "$PR_NUM" --merge --admin || echo "Failed to merge PR $PR_NUM"
done

echo "Merge to minimal set completed"
