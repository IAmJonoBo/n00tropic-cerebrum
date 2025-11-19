# ADR-006: Planner Telemetry Surfaces & Docs Migration Gap Closure

## Status

Proposed – 2025-11-19

## Context

Temp-doc (planner directive) and temp-doc-2 (Antora migration + Typesense) are largely implemented, but recent audits surfaced remaining gaps:

1. Planner outputs exist (Danger metrics, nightly runs) yet lack surfaced telemetry (dashboards, learning logs) and automatic plan attachments to briefs.
2. Typesense configuration/workflow exists, but no recorded remote reindex validation and several repos still rely on legacy Markdown (policies, pipelines, learning logs).
3. PM/control-panel docs do not summarise planner health, Typesense validation, or migration status.

## Decision

Close the directive gaps with the following projects:

1. **Planner Telemetry Surfaces**
   - Publish planner metrics dataset (n00-school) + n00-cortex dashboards; update docs referencing them.
   - Extend n00-horizons automation so experiment brief PRs commit deterministic `.plan.md` artefacts.
   - Add planner status to AGENT_E2E runbook and control-panel doc.

2. **Antora & Typesense Completion**
   - Convert remaining Markdown (n00tropic policies, n00-school learning logs, n00clear-fusion pipeline details, n00plicate legacy quality/security/testing guides) to Antora pages.
   - Document and execute a remote Typesense reindex run (Actions workflow with secrets) and log the result (learning log entry + docs update).
   - Update migration tracker when each repo hits ✅ (nav parity + major docs converted).

3. **Control-Panel Enhancements**
   - Aggregate planner metrics, Typesense validation status, and docs migration progress into the control-panel doc for PM visibility.

## Consequences

- Provides end-to-end telemetry (plans can be audited without digging through artifacts).
- Eliminates remaining Markdown-only knowledge bases, ensuring search/Typesense index all docs.
- PM tooling gains visibility into documentation + planner health, enabling future prioritisation.

## Follow-up

- Track each workstream via n00-horizons experiment + jobs (see `docs/modules/ROOT/pages/closing-gaps.adoc`).
- Once completed, mark temp-doc/temp-doc-2 as done in docs + migration tracker.
