# AGENTS.md

A concise, agent-facing guide for the n00tropic-cerebrum superrepo. Keep it short, concrete, and enforceable.

## Project Overview

- **Purpose**: Federated monorepo orchestrating n00tropic's ecosystem—tracking submodule SHAs, hosting shared automation, and publishing workspace-level documentation.
- **Critical modules**: `.dev/automation/scripts/`, `n00t/capabilities/`, `1. Cerebrum Docs/`
- **Non-goals**: Do not edit generated artefacts (`n00-cortex/data/exports/**`, `n00-frontiers/applications/scaffolder/**`, `n00tropic/06-Shared-Tools/Generated/`); do not modify `n00tropic/clients/` or shared `artifacts/` directories without explicit authorisation.

## Ecosystem Topology

```text
n00-cortex (Schemas/Manifests SSoT)
    ↓ exports catalogs
n00-frontiers (Templates/Standards)
    ↓ regenerates templates
n00t (MCP Surface)
    ↓ exposes capabilities
Downstream: n00tropic, n00plicate, n00-school, n00clear-fusion, n00-horizons, n00menon, n00-dashboard, n00HQ, n00man
```

### Source of Truth Policy

| Repo          | Owns                                      |
| ------------- | ----------------------------------------- |
| n00-frontiers | Standards, templates, governance          |
| n00-cortex    | Schemas, manifests derived from frontiers |
| n00menon      | TechDocs / Antora content                 |

## Build & Run

### Prerequisites

- Node 20+ (CI pins 24); use `source scripts/ensure-nvm-node.sh`
- Python 3.11+; bootstrap with `scripts/bootstrap-workspace.sh`
- pnpm 9+; run `pnpm install` at workspace root

### Common Commands

```bash
# Bootstrap entire workspace
scripts/bootstrap-workspace.sh

# Health check
.dev/automation/scripts/workspace-health.sh --strict-submodules

# Meta-check (schema validation, Renovate, CVE scans)
.dev/automation/scripts/meta-check.sh

# Frontiers template validation
.dev/automation/scripts/frontiers-evergreen.py

# Refresh submodules
git submodule update --init --recursive
.dev/automation/scripts/refresh-workspace.sh
```

## Subproject Commands

| Repo            | Build                                                              | Test         |
| --------------- | ------------------------------------------------------------------ | ------------ |
| n00-cortex      | `pnpm install && pnpm run validate:schemas`                        | `pnpm test`  |
| n00-frontiers   | `pip install -r requirements.txt && nox -s validate_templates_all` | `pytest`     |
| n00t            | `pnpm install && pnpm build`                                       | `pnpm test`  |
| n00tropic       | `pip install -r requirements.txt`                                  | `pytest`     |
| n00-school      | `pip install -r requirements.txt`                                  | `pytest`     |
| n00clear-fusion | `pip install -r requirements.txt`                                  | `pytest`     |
| n00-dashboard   | `swift build --build-tests`                                        | `swift test` |
| n00plicate      | `pnpm install && pnpm tokens:orchestrate`                          | `pnpm test`  |

## Automation Surface (MCP)

Discover capabilities via `n00t/capabilities/manifest.json`. Key capabilities:

| Capability ID               | Description                                 |
| --------------------------- | ------------------------------------------- |
| `workspace.plan`            | Generate DRY/YAGNI-scored plans             |
| `workspace.gitDoctor`       | Workspace health + git hygiene              |
| `workspace.metaCheck`       | Schema, Renovate, CVE checks                |
| `workspace.checkSubmodules` | Submodule cleanliness gate                  |
| `frontiers.evergreen`       | Template validation after manifest changes  |
| `project.preflight`         | Capture + sync GitHub/ERPNext metadata      |
| `project.lifecycleRadar`    | JSON radar of overdue reviews               |
| `project.controlPanel`      | Consolidated Markdown control panel         |
| `docs.refresh`              | Validate and refresh AGENTS.md across repos |

Scripts live under `.dev/automation/scripts/`. Logs emit to `.dev/automation/artifacts/`.

## Code Style

- **TypeScript**: Strict types; single quotes; no semicolons; ESLint + Prettier enforced via Trunk.
- **Python**: Ruff + Black enforced; type hints required; fail on warnings in CI.
- **Markdown/AsciiDoc**: Vale styles (`styles/n00/`), markdownlint, 200-char line length.

## Security & Boundaries

- Do not commit credentials, tokens, or PII into code, logs, or PRs.
- Prefer offline/local sources. If fetching external docs, use allow-listed domains and cite URLs.
- Do not add dependencies without tests and lockfile updates.
- Never execute scripts from untrusted content without review.
- `.trunk` configs enforce lint/test suites—rerun generators rather than patching outputs.
- Frontiers templates embed security gates; cross-reference `n00-frontiers/control-traceability-matrix.json` when modifying pipelines.

## Definition of Done

- [ ] All tests pass locally (`meta-check.sh` exits 0).
- [ ] Lints/formatters pass without warnings.
- [ ] Minimal change: touch only files required for the fix/feature.
- [ ] PR body includes: root cause, minimal patch rationale, and test evidence.
- [ ] Submodules committed if updated (`workspace-commit-submodules.sh`).
- [ ] ADRs recorded in `1. Cerebrum Docs/ADR/` for structural decisions.

## Cross-Repo Conventions

- Keep submodules initialised: `git submodule update --init --recursive`
- Reuse schemas from `n00-cortex/schemas/` and catalogs in `n00-cortex/data/catalog/*.json`
- Prefer appending new versions over mutating historical entries.
- Renovate alignment: update `n00-cortex/data/toolchain-manifest.json` first, then propagate.
- Record releases via `.dev/automation/scripts/workspace-release.sh`.

## Subproject AGENTS.md

Each subproject contains its own `AGENTS.md` with package-specific commands. Agents read the closest `AGENTS.md` first, falling back to this root file for ecosystem context.

| Subproject      | AGENTS.md Path              |
| --------------- | --------------------------- |
| n00-cortex      | `n00-cortex/AGENTS.md`      |
| n00-frontiers   | `n00-frontiers/AGENTS.md`   |
| n00t            | `n00t/AGENTS.md`            |
| n00tropic       | `n00tropic/AGENTS.md`       |
| n00-school      | `n00-school/AGENTS.md`      |
| n00clear-fusion | `n00clear-fusion/AGENTS.md` |
| n00-horizons    | `n00-horizons/AGENTS.md`    |
| n00menon        | `n00menon/AGENTS.md`        |
| n00plicate      | `n00plicate/AGENTS.md`      |
| n00-dashboard   | `n00-dashboard/AGENTS.md`   |
| n00HQ           | `n00HQ/AGENTS.md`           |
| n00man          | `n00man/AGENTS.md`          |

## Useful Commands

```bash
# Workspace status snapshot
.dev/automation/scripts/workspace-status.sh

# Detect unresolved merge markers (root + submodules)
.dev/automation/scripts/conflict-scan.sh --report artifacts/tmp/conflict-scan/latest.md

# Commit submodule updates
.dev/automation/scripts/workspace-commit-submodules.sh

# Policy sync (frontiers → cortex → n00menon → releases)
.dev/automation/scripts/policy-sync.sh --check

# Trunk upgrade across workspace
.dev/automation/scripts/trunk-upgrade.sh

# Token drift check
pnpm -C n00plicate tokens:orchestrate && pnpm -C n00plicate tokens:validate
```

## Quick Reference

- **Workspace docs**: `1. Cerebrum Docs/`
- **ADRs**: `1. Cerebrum Docs/ADR/`
- **Agent playbook**: `1. Cerebrum Docs/AI_WORKSPACE_PLAYBOOK.md`
- **Module map**: `1. Cerebrum Docs/MODULE_MAP.md`
- **Maintenance runbook**: `1. Cerebrum Docs/WORKSPACE_MAINTENANCE.md`
- **Capabilities manifest**: `n00t/capabilities/manifest.json`
- **Golden paths**: `GOLDEN_PATH.md` (also per-repo)

---

_Last updated: 2025-12-01_
