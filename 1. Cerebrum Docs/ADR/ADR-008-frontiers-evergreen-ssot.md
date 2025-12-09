# ADR-008: Frontiers Evergreen SSoT Charter

## Status

Proposed – 2025-11-29

## Context

n00-frontiers produces the canonical templates, scaffolds, and automation metadata that flow into n00-cortex catalogs and n00tropic generators. As frameworks evolve, the repo drifts unless we:

- restate its scope and KPIs in living docs (README, CATALOG, BIBLE) so teams know what “fresh” means,
- couple schema/manifest changes in n00-cortex to automatic template validation/exports,
- expand template coverage (SwiftUI, packaging, cookiecutters) backed by documented workflows, and
- surface freshness gaps through lifecycleRadar/controlPanel automation so overdue artefacts are visible.

Without an explicit charter, downstream repos risk stale templates, missing scaffolders, and silent failures in generators that assume frontiers is the single source of truth.

## Decision

1. **Codify scope + metrics** – Refresh `n00-frontiers/README.md`, `docs/CATALOG.md`, and `docs/BIBLE.md` with authoritative scope, freshness SLAs, and dependency diagrams that tie into `1. Cerebrum Docs/WORKSPACE_MAINTENANCE.md`.
2. **Tighten dependency hooks** – Whenever `n00-cortex/data/toolchain-manifest.json` or frontiers schemas change, run `.dev/validate-templates.sh --all` and publish artefacts, failing automation if exports drift. Wire the hook through an MCP capability so humans and agents share the workflow.
3. **Expand template families** – Introduce SwiftUI, Swift Package Manager, and packaging scaffolders (deb/rpm/homebrew) beneath `n00-frontiers/templates/`, each backed by cookiecutter definitions and pnpm wrappers for reproducibility.
4. **Lifecycle telemetry** – Ensure `project.lifecycleRadar` and `project.controlPanel` ingest frontiers review metadata, highlighting overdue templates plus integration blockers.
5. **Traceability contract** – Document how n00tropic generators consume frontiers exports and require new templates to ship validation scripts, sample outputs, and integration notes before they’re marked stable.

## Consequences

- Positive: Every consumer knows frontiers is authoritative, with explicit KPIs and review cycles.
- Positive: Automation catches drift as soon as schemas or manifests change, reducing silent regressions.
- Positive: Swift/packaging teams get first-class scaffolders instead of ad-hoc forks.
- Negative: Bootstrap time increases because validate/export hooks run more often; mitigation via cached runners is required.
- Negative: Contributors must update lifecycle metadata for each template, adding process overhead.

## Implementation Notes

- Add a new Control Panel section summarizing frontiers freshness (review windows, validation artifacts).
- Track feature work via a dedicated n00-horizons job (`job-frontiers-evergreen-ssot`) so lifecycleRadar can report progress.
- Record automation outputs under `.dev/automation/artifacts/automation/frontiers-evergreen-*.json` for observability.
- Provide a shared automation entrypoint via
  `.dev/automation/scripts/frontiers-evergreen.py` and the n00t capability
  `frontiers.evergreen` so runners, agents, and humans all trigger the same
  validation/export pipeline.
- Encourage OSS-first tooling (Cookiecutter, SwiftPM, pnpm) before introducing bespoke runners; only build custom scripts when cross-repo coordination demands it.
