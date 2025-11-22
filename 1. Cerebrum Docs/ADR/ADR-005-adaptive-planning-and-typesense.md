# ADR-005: Adaptive Planning Engine & Typesense Search

## Status

Accepted - 2025-11-19

## Context

Two directives landed simultaneously:

1. **Codex Planning Directive (temp-doc.md)** - requires every brief/issue to start with a DRY/YAGNI-scored plan emitted as an MCP packet, powered by a new `n00t/planning/` runtime, automation hooks, and n00-school telemetry.
2. **Antora migration + search blueprint (temp-doc-2.md)** - finishes the multi-repo docs migration and mandates an OSS-first search stack with Lunr offline support and Typesense (local container-preferred, remote optional) for production indexing.

Executing piecemeal risks drift: planners could emit non-compliant plans, or docs might ship without search/index validation. We need a unified decision so every team understands scope, boundaries, and guardrails.

## Decision

- **Adopt Adaptive Planning Engine v1**
  - Build the runtime exclusively inside `n00t/planning/` (CrewAI + LiteLLM + MCP surface) and expose it via a new capability manifest entry plus `.dev/automation/scripts/plan-exec.sh`.
  - Every plan output is dual-format: MCP packet and Markdown `.plan.md` stored alongside briefs. Plans MUST carry DRY/YAGNI/conflict metadata and become training examples (JSONL) for n00-school’s planner pipeline.
  - Automation (meta-check, lifecycle radar, Danger) treats missing/stale plans as blockers for docs/brief PRs.

- **Standardize on Typesense for search**
  - Typesense container (official OSS image) is the default deployment. Provide `docs/search/docsearch.typesense.env.example` and `typesense-compose.yml` for local builds; remote endpoints may be configured via env overrides when a shared cluster exists.
  - Lunr remains enabled for offline builds; Algolia stays as historical fallback but no longer the primary.
  - Add a `search-reindex.yml` workflow that spins up Typesense, runs the OSS docsearch scraper, and tears it down post-index.

- **Governance & Documentation**
  - Publish `docs/PLANNING.md` (3-minute guide) and `docs/modules/ROOT/pages/planning.adoc` referencing this ADR.
  - Update n00-horizons experiment templates with `[[PLAN]]` anchors; AGENT_E2E runbook enumerates validation steps (planner run, Antora build, Typesense index, MCP docs sanity).

## Implementation

- Planner CI (`.github/workflows/planner.yml`) and Danger rules now gate `.plan.md` files, ensuring DRY/YAGNI/conflict metrics block PRs when thresholds are exceeded.
- `n00-school/pipelines/planner-v1.yml` ingests plan telemetry; the learning log entry dated 2025-11-19 captures the dataset wiring.
- Typesense now ships with a repeatable workflow: `docs/search/README.adoc` documents the dockerised scraper, `.github/workflows/search-reindex.yml` uses `typesense/docsearch-scraper:0.9.0`, and logs live under `docs/search/logs/` (latest: `typesense-reindex-20251119.log`).
- Antora navs reference the migrated policy/quality/testing pages so Typesense indexes their attributes.

## Consequences

- Positive: Plans, docs, and search infrastructure share a single workflow, reducing manual coordination.
- Positive: OSS-first Typesense setup keeps costs minimal and reproducible (local container for dev, remote optional for Ops).
- Positive: n00-school gains a consistent dataset for adaptive training, feeding back into planner quality.
- Negative: CI complexity increases (planner workflow, search re-index, Antora for every repo). M1 runners must allocate CPU/RAM carefully.
- Negative: Teams must learn new rituals (`n00t plan`, Typesense compose, nightly planner training). Provide enablement sessions + updated runbooks.

## Implementation Steps

1. Land `docs/PLANNING.md`, `docs/modules/ROOT/pages/planning.adoc`, and reference this ADR from nav/runbooks.
2. Scaffold `n00t/planning/` modules + tests, register capability manifest entry, and add `.dev/automation/scripts/plan-exec.sh` + `plan-resolve-conflicts.py`.
3. Update n00-horizons experiment templates + AGENT_E2E runbook with `[[PLAN]]` anchor + Typesense steps.
4. Create `n00-school/pipelines/planner-v1.yml`, handlers, datasets, and nightly automation; log planner telemetry to `agent-runs.json`.
5. Commit Typesense configs (`docs/search/README.adoc`, env example, docsearch config), compose file, and `search-reindex.yml` GitHub Action.
6. Finish Antora migration per repo, update `antora-playbook.yml`, ensure `scripts/check-attrs.mjs`, Vale, and Lychee cover new pages.
7. Add `.github/workflows/planner.yml` gating YAGNI/conflicts and tie Danger warnings to stale `:reviewed:` metadata.

## Follow-up Questions

- Do we need a lightweight UI (n00t control-centre) to visualize planner telemetry + Typesense status?
- Should Typesense live in a persistent workspace service (e.g., managed VM) instead of ephemeral containers once scale grows?
- Can we reuse planner telemetry to auto-suggest scope cuts in n00-horizons experiments?
