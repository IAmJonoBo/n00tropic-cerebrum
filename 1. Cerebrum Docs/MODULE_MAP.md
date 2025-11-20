# n00tropic Cerebrum Module Map

This document summarises the major modules in the `n00tropic-cerebrum` workspace and how they fit together.

## Superrepo: n00tropic-cerebrum

- Role: Orchestration shell for the ecosystem, tracking submodule SHAs and hosting shared automation + workspace docs.
- Key assets:
  - `1. Cerebrum Docs/`: ADRs, releases, workspace maintenance guides.
  - `.dev/automation/scripts/`: workspace-wide automation entrypoints.
  - `.gitmodules`: lists submodules and their upstream remotes.

## n00-cortex

- Role: Source of truth for schemas, catalogs, and automation metadata.
- Interfaces:
  - Consumed by `n00-frontiers` via exported catalogs (`data/` and `exports/`).
  - Touched by `cortex.frontiersIngest` capability (defined in `n00t`).

## n00-frontiers

- Role: Templates, controls, and delivery pipelines that consume Cortex catalogs.
- Interfaces:
  - Generates assets that are ingested into `n00-cortex`.
  - Drives workspace sanity/validation via frontiers-oriented scripts.

## n00t

- Role: Automation control center and MCP surface.
- Interfaces:
  - `capabilities/manifest.json` declares workspace, dependency, AI workflow, and module-specific capabilities.
  - Capabilities map to root `.dev/automation/scripts/**` and to module scripts in `n00-school` and others.

## n00-school

- Role: ML training and evaluation orchestration.
- Interfaces:
  - Exposed via `school.trainingRun` capability in `n00t`.
  - Relies on pipeline definitions and datasets under its own tree.

## n00plicate

- Role: Specialized generators / utilities (e.g. content or code duplication tooling).
- Interfaces:
  - Consumes schemas and catalogs from `n00-cortex` where relevant.

## n00tropic

- Role: Core AI design generator and related tooling.
- Interfaces:
  - Consumes cortex schemas and frontiers templates.

## n00clear-fusion

- Role: Experimental or advanced fusion / integration tooling for the ecosystem.
- Interfaces:
  - Consumes upstream schemas and automation, may emit artefacts used by other modules.

## n00-horizons

- Role: Prototyping, horizons / experimental space for future modules.
- Interfaces:
  - Loosely coupled; may depend on cortex/frontiers for schemas and templates.

---

For detailed automation and capability contracts, see `n00t/capabilities/manifest.json` and the workflow docs in `1. Cerebrum Docs/AI_WORKSPACE_PLAYBOOK.md` and `1. Cerebrum Docs/WORKSPACE_MAINTENANCE.md`.
