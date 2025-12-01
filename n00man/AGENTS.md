# AGENTS.md

A concise, agent-facing guide for n00man. Keep it short, concrete, and enforceable.

## Project Overview

- **Purpose**: Agent factory for n00tropic—scaffolds, governs, and registers new
  agents so they meet frontier standards and integrate cleanly with the superrepo.
- **Critical modules**: (scaffolding only)
- **Non-goals**: Not yet production-ready; agent scaffolding logic is pending.

## Status

✅ **Agent foundry core online.** Python package `n00man.core` now exposes the
AgentFoundryExecutor, registry helpers, and scaffold generator.

Available features:

- CLI-driven scaffolding with JSON registry updates
- Agent profile, capability manifest, and executor stub generation

Planned features:

- Governance rules and validation
- Registration with n00t capability manifest
- Integration testing for new agents

## Build & Run

### Prerequisites

- TBD (likely Python 3.11+ or Node 20+)

### Common Commands

```bash
# Scaffold a new agent profile + executor
python -m n00man.cli scaffold \
  --name brand-reviewer \
  --role "Brand Reviewer" \
  --description "Reviews assets for brand compliance" \
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

- [ ] Build succeeds (when implemented).
- [ ] Tests pass (when added).
- [ ] Scaffolded agents meet frontier standards.
- [ ] PR body includes rationale and test evidence.

## Integration with Workspace

When in the superrepo context:

- Root `AGENTS.md` provides ecosystem-wide conventions.
- Will register agents in `n00t/capabilities/manifest.json`.
- Will consume templates from `n00-frontiers`.

---

_For ecosystem context, see the root `AGENTS.md` in n00tropic-cerebrum._

_Status: Scaffolding only — under construction._

---

_Last updated: 2025-12-01_
