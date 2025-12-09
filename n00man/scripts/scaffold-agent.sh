#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="${1-}"
ROLE="${2-}"
if [[ -z ${NAME} || -z ${ROLE} ]]; then
	echo "Usage: $0 <agent-name> <role>" >&2
	exit 1
fi

python3 "$ROOT_DIR/cli/main.py" scaffold \
	--name "${NAME}" \
	--title "${NAME}" \
	--role "${ROLE}" \
	--description "Auto-generated profile for ${ROLE}"

node "$ROOT_DIR/../scripts/enforce-doc-tags.mjs" --root "$ROOT_DIR"
