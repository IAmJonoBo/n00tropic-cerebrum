#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="${1:-}"
ROLE="${2:-}"
if [[ -z "$NAME" || -z "$ROLE" ]]; then
  echo "Usage: $0 <agent-name> <role>" >&2
  exit 1
fi

slug="$NAME"
agent_dir="$ROOT_DIR/docs/agents/$slug"

mkdir -p "$agent_dir"

cat >"$agent_dir/agent-profile.adoc" <<EOF
:page-tags: diataxis:reference, domain:platform, audience:agent, stability:beta
:reviewed: $(date +%Y-%m-%d)

= Agent profile — ${NAME} (${ROLE})

Role

* ${ROLE}

Responsibilities

* Outline key responsibilities here.

Capabilities & tools

* Document required toolchains, MCP capabilities, and data sources.

Inputs

* List briefs/inputs.

Outputs

* Define expected artefacts and quality bars.

Success criteria

* Define measurable outcomes.
EOF

node "$ROOT_DIR/../scripts/enforce-doc-tags.mjs" --root "$ROOT_DIR"

echo "[scaffold-agent] Created $agent_dir/agent-profile.adoc"
