# AI‑Heavy Discovery — Facilitator Guide (90 minutes)

**Audience:** Product, Eng, AI/ML, Design, Security, Data, Ops.  
**Goal:** Decisions over direction; risks owned; spikes queued; ADRs drafted.

## Prep (15–30 min before)

- Print the **10‑minute intake**; skim for blanks and assumptions.
- Prepare a decision log and an **ADR backlog** sheet.
- Open a timer. Timeboxes are real.

## Ground rules (read aloud)

- Be specific. If you don’t know, say “unknown” and log a spike.
- Prefer reversible choices; controversial ones become ADRs.
- Safety beats speed. If risky, add a guardrail.

## Agenda & outcomes

1. **Outcomes & tasks (10)** → Top 3 outcomes; 5–8 atomic tasks; pass criteria per task.
2. **Autonomy & HITL (10)** → Autonomy map; HITL gates; compensations.
3. **Models & routing (10)** → Candidate models; routing/fallback; degraded mode.
4. **Prompts & output contracts (10)** → Persona; canonical instructions; JSON schema.
5. **Tools & permissions (10)** → Tool list; least privilege; idempotency/transactions.
6. **RAG & freshness (10)** → Sources; indexing; freshness; provenance.
7. **Safety & policy (10)** → Prevent/Detect/Respond matrix; incident playbook.
8. **Quality & evals (10)** → Offline/online metrics; approval tests; regression gates.
9. **Delivery & rollback (5)** → Flags; canary/blue‑green; rollback drills.
10. **Risks & decisions (5)** → Owners, dates, success criteria.

## Parking lot

Capture tangents and big ideas. Revisit only if time remains.

## Artefacts to produce (during/after)

- Updated **Intake**; **Agent System Spec** outline.
- **Guardrail Matrix** (Prevent/Detect/Respond).
- **AI Evaluation Plan** skeleton with metrics & datasets.
- **ADR backlog** with decision owners & dates.
- **Spike list** (≤ 1 week each) with stop/go criteria.

## Definition of done (workshop)

- Everyone can state the top 3 outcomes in one sentence.
- Autonomy & HITL are explicit per task.
- Output contracts exist as JSON schemas.
- Safety risks have named guardrails & owners.
- At least 3 ADRs drafted or queued.
- Next checkpoint scheduled.

**Tone:** candid, time‑boxed, and allergic to hand‑waving.
