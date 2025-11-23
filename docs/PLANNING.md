# Adaptive planning & Antora migration plan

_Last updated: 2025-11-19_

## Scope

- Ship the Codex planning engine inside `n00t/planning/` with MCP + CrewAI + LiteLLM loops, resolver/executor orchestration, and telemetry for n00-school.
- Refresh PM artefacts (experiment briefs, templates, AGENT_E2E runbooks) so every brief/issue starts with a DRY/YAGNI-scored plan and conflict resolutions.
- Finish the multi-repo Antora migration and light up a Typesense-powered search stack (local container by default, remote OSS-friendly endpoint optional).
- Enforce CI/automation hooks: planner workflow, attr/Danger guardrails, Typesense re-index, and nightly planner training runs.

## Workstreams and leads

| Workstream       | Leads                    | Key Outputs                                                                                                |
| ---------------- | ------------------------ | ---------------------------------------------------------------------------------------------------------- |
| Planning runtime | Codex + n00t maintainers | `n00t/planning/` package, planner capability manifest, CLI entrypoints, `.plan.md` artefacts               |
| PM + telemetry   | Horizons + School        | Updated experiment templates, AGENT_E2E updates, `n00-school/pipelines/planner-v1.yml`, agent-runs dataset |
| Docs + search    | Docs guild               | `docs/modules/ROOT/pages/planning.adoc`, Typesense README/configs, docsearch workflow, MCP docs updates    |
| Antora migration | All repo owners          | `docs/antora.yml` + module trees in every `n00*` repo, tracker entries, nav refresh                        |

## Milestones

1. **Planner foundation** (Week 1)
   - Scaffold `n00t/planning/` (engine, agents, adapters, tests) and publish `docs/modules/ROOT/pages/planning.adoc`.
   - Register `plan-exec.sh` + `plan-resolve-conflicts.py`, update `n00t/capabilities/manifest.json`, and add CLI verb + Danger hooks.
2. **Telemetry & training** (Week 2)
   - Extend n00-horizons templates with `[[PLAN]]`, link AGENT_E2E runbook updates, and land `docs/PLANNING.md` walk-through.
   - Add `n00-school/pipelines/planner-v1.yml`, handlers, dataset plumbing, and planner CI workflow gating YAGNI/conflicts.
3. **Typesense + Antora** (Week 3)
   - Deliver `docs/search/README.adoc`, `docsearch.config.json`, environment examples, and GitHub Actions `search-reindex.yml` that spins a local container.
   - Finish Antora conversions in remaining repos, update `antora-playbook.yml`, and verify Lunr + Typesense indexes locally.
4. **System validation** (Week 4)
   - Run `.dev/automation/scripts/meta-check.sh`, `workspace-health`, planner CI, Typesense re-index, and create sample `.plan.md` for PR showcase.
   - Capture M1 benchmark + dataset snippets for PR body and cut `[Codex] Planning Engine v1 - MCP-native, air-gapped, self-training, adaptive PM`.

## Readiness checklist

- [x] `n00t/planning/` passes unit tests and integrates with `n00t plan`.
- [x] Planner capability published + `.dev/automation/scripts/plan-exec.sh` accessible via MCP + CLI.
- [x] `docs/modules/ROOT/pages/planning.adoc` + this file stay in sync (link from nav + AGENT_E2E runbook).
- [x] Experiment briefs/template adopt `[[PLAN]]` anchor and conflict resolution guidance.
- [ ] `n00-school/pipelines/planner-v1.yml` live with telemetry ingestion + nightly `n00t school.trainingRun planner-v1` job scheduled (pipeline ready; scheduling pending).
- [x] Typesense container compose + remote override documented; `search-reindex.yml` succeeding with OSS image (see `docs/search/logs/typesense-reindex-20251119.log`).
- [x] Antora tracker rows updated for every repo once their PRs land.
- [x] Planner CI + Danger gating (YAGNI < 0.3, no stale `:reviewed:`) enforced on all doc/brief PRs.

## References

- Temp directives: `stuff/Temp/temp-doc.md`, `stuff/Temp/temp-doc-2.md`.
- ADR-005 (new) for adaptive planning + Typesense.
- `1. Cerebrum Docs/Agent Assisted Development/AGENT_E2E_RUNBOOK.md` for hands-on validation steps.
