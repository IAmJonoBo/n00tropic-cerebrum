# Handover Contract (n00tropic)

_Frank, short, and enforceable. CI should block merges if this is incomplete._

## 1) Essentials

- **Service/module name:**
- **Owner(s) / escalation:**
- **Purpose (one paragraph):**
- **Quickstart:** commands/env/secrets required (links to READMEs).

## 2) Architecture snapshot (C4)

- Context/Containers/Components links (images or PlantUML/Mermaid).
- Trust boundaries & cross-cutting concerns called out.

## 3) Decisions since last handover

- ADR list with status + consequences (link to `/docs/architecture/ADRs/`).

## 4) Contracts

- **API**: OpenAPI/GraphQL links, version, breaking changes flagged.
- **Async**: AsyncAPI/events, topics, schemas, delivery guarantees.
- **Deprecations**: timelines and migration notes.

## 5) Operate it

- **Runbooks**: start/stop, common failures, playbooks.
- **Dashboards & alerts**: links; owners; on-call rota.
- **SLOs**: SLIs, targets, error budgets, burn-rate alerting.

## 6) Quality gates & test status

- Coverage on critical paths: \_\_%
- Static analysis (new high/critical = 0): pass/fail
- Perf budgets & results: (budgets, last test date)
- Secrets scan: pass/fail

## 7) Security & privacy

- Threat model status (date), ASVS level/controls coverage.
- Data classes (PII), residency, retention policy.

## 8) Known risks, debts, and TODOs

- Top 5 items with owners and dates.

## 9) Releases since last handover

- Version(s), highlights, migrations, breaking changes.

> Generate a packet with `make handover`. Store packet under `/handover/` per release.
