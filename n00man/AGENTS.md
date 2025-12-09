# AGENTS.md

A concise, agent-facing guide for n00man. Keep it short, concrete, and enforceable.

## Project Overview

- **Purpose**: Agent factory for n00tropic—scaffolds, governs, and registers new
  agents so they meet frontier standards and integrate cleanly with the superrepo.
- **Critical modules**: `n00man/core/foundry.py`, `n00man/core/governance.py`,
  `n00man/docs/agent-registry.json`, `n00man/schemas/agent-profile.schema.json`
- **Non-goals**: Do not hand-edit generated docs in `n00man/docs/agents/**`; rerun
  the scaffold instead. Guardrails live in frontiers policy (`n00-frontiers/frontiers/policy/agent-roles.yml`).

## Status

✅ **Agent foundry core online.** Python package `n00man.core` now exposes the
AgentFoundryExecutor, registry helpers, and scaffold generator.

Available features:

- CLI-driven scaffolding with JSON registry updates
- Agent profile, capability manifest, and executor stub generation
- Schema-driven governance validation (JSON Schema + frontiers roles)

Planned features:

- n00t MCP capability wiring (`n00man.scaffold`, `n00man.validate`, `n00man.list`)
- Integration/evaluation harnesses before production rollout

## Build & Run

### Prerequisites

- Python 3.11+
- `pip install -r requirements.workspace.txt` (root) or `uv pip install jsonschema`

### Common Commands

```bash
# Scaffold a new agent profile + executor
python -m n00man.cli scaffold \
  --name brand-reviewer \
  --role reviewer \
  --description "Reviews assets for brand compliance" \
  --owner brand-studio \
  --model-provider openai \
  --model-name gpt-5.1-codex \
  --model-fallback openai/gpt-5.1-codex-mini \
  --tag brand --tag creative

# List registered agents from docs/agent-registry.json
python -m n00man.cli list
```

## Code Style

- Follow `n00-frontiers` conventions when implementing.
- Agents must meet frontier standards.
- Generated executors rely on `agent_core` shipped in `n00t/packages/agent-core`.

## Security & Boundaries

- Do not commit credentials or secrets.
- All scaffolded agents must pass governance validation.
- Follow workspace conventions once implementation begins.

## Definition of Done

- [ ] `python -m pytest n00man/tests` passes.
- [ ] `python -m n00man.cli scaffold ...` produces docs + updates registry.
- [ ] Governance validation passes (schema + roles + guardrails).
- [ ] PR body includes rationale and test evidence.

## Integration with Workspace

When in the superrepo context:

- Root `AGENTS.md` provides ecosystem-wide conventions.
- Will register agents in `n00t/capabilities/manifest.json`.
- Will consume templates from `n00-frontiers`.

---

_For ecosystem context, see the root `AGENTS.md` in n00tropic-cerebrum._

_Status: Scaffolding + governance complete; MCP wiring in progress._

---

_Last updated: 2025-12-01_
