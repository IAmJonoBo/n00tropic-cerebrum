# Scope-Change Protocol (n00tropic)

**Why:** Scope changes without artifacts = chaos later. This protocol ensures consumers and operators can adapt smoothly.

## 1) Propose

- Open an **RFC issue** using `/docs/templates/ScopeChangeRFC.md`.
- Include impact analysis, acceptance tests, and rollout plan.

## 2) Codify

- Update **ADRs** (context → decision → consequences).
- Update **contracts** (OpenAPI/GraphQL/AsyncAPI) and bump versions.
- Provide migration notes & deprecation timelines.

## 3) Communicate

- Notify owners (CODEOWNERS auto-tag) and update service catalog (Backstage).
- Link dashboards/alerts if observability changes.

## 4) Verify

- Add/adjust tests & performance budgets; confirm CI **Quality Gates** green.
- For breaking changes, run canary and have rollback prepared.

**Definition of done:** RFC merged, ADR merged, contracts versioned & published, tests updated, ops docs updated, release notes drafted.
