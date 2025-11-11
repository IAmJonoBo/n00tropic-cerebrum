# Discovery Workshop — Facilitator Guide (90 minutes)

**Audience:** Product, Eng, Design, Security, Data, QA, Ops.  
**Goal:** Decisions over direction; risks owned; spikes queued; ADRs drafted.

## Prep (15–30 min before)

- Print the **10‑minute intake**; highlight blanks and assumptions.
- Prepare a decision log and an **ADR backlog** sheet.
- Open a timer. Timeboxes are not a suggestion.

## Ground rules (read aloud)

- Be specific. If unknown, say “unknown” and log a spike.
- Prefer reversible choices; controversial ones become ADRs.
- Quality > speed. If risky, add a guardrail or a feature flag.

## Agenda & outcomes

1. **Outcomes & metrics (10)** → Top 3 outcomes; KPIs; definition of done.
2. **Users & UX (10)** → Jobs, flows, accessibility constraints.
3. **Scope & constraints (10)** → In/out; dependencies; regulators.
4. **Architecture (C4) (10)** → Context/containers/components; trust boundaries.
5. **Data & contracts (10)** → APIs, schemas, ownership, migrations.
6. **NFRs (10)** → SLOs, perf budgets, security/privacy/compliance.
7. **DevEx & toolchain (10)** → Criteria; repo layout; hooks.
8. **Testing & gates (10)** → Pyramid, coverage, static analysis, perf budgets.
9. **CI/CD & release (5)** → Stages, flags, canary/blue‑green, rollback.
10. **Observability & ops (5)** → Dashboard/alerts, SLOs, DR.
11. **Risks & decisions (5)** → Owners, dates, success criteria.

## Parking lot

Capture tangents and bright ideas. Revisit only if time remains.

## Artefacts to produce (during/after)

- Updated **Intake**; **Architecture Overview** outline.
- **Quality Gates** & **Test Strategy** skeletons.
- **ADR backlog** with decision owners & dates.
- **Spike list** (≤ 1 week) with stop/go criteria.

## Definition of done (workshop)

- Everyone can state the top 3 outcomes in one sentence.
- Scope and constraints are explicit.
- C4 snapshot exists with trust boundaries.
- NFRs are measurable (SLOs/perf budgets).
- At least 3 ADRs drafted or queued.
- Next checkpoint scheduled.

**Tone:** candid, time‑boxed, allergic to hand‑waving.
