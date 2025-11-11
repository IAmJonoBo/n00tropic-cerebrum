# n00tropic — AI‑Heavy Discovery Questionnaire

_Witty, intelligent, frank. We build agents that do real work, not party tricks._

> **Purpose.** This intake maps directly to: `/docs/ai/AGENT_SYSTEM_SPEC.md`, `/docs/ai/AI_GUARDRAILS.md`, `/docs/ai/AI_EVALUATION_PLAN.md`, `/docs/architecture/ARCHITECTURE_OVERVIEW.md`, `/docs/policies/THREAT_MODEL.md`, `/docs/quality/TEST_STRATEGY.md`, `/docs/ops/OBSERVABILITY_SPEC.md`.
> Fill what you know now; turn unknowns into spikes/ADRs. Keep answers concrete and measurable.

---

## 0) Executive Snapshot (AI edition — one page)

- **Working title & elevator pitch (one sentence):**
- **Primary use cases (ranked):**
- **Quality bar:** What does “correct” look like? What’s unacceptable?
- **Guardrails summary:** Top risks + how we’ll prevent them.
- **SLAs/SLOs:** p95 latency, availability, freshness, error budget.
- **Cost guardrail:** max $/task or tokens/task (p50/p95).

---

## 1) Outcomes & Tasks

- **Target outcomes (3–5, measurable):**
- **Task inventory:** List atomic tasks the agent must perform.
- **Success definition per task:** pass criteria, gold answers, oracles.
- **Constraints:** legal, policy, domain rules the agent must honour.

---

## 2) Autonomy & Human‑in‑the‑Loop (HITL)

- **Autonomy level per task:** Inform → Suggest → Approve → Execute → Execute+Notify.
- **HITL points:** where humans review/approve/escalate.
- **Reversibility:** compensation actions / undo plan per risky action.
- **Auditability:** what evidence must be stored for decisions?

---

## 3) Model Portfolio & Providers

- **Vendors/models under consideration:** (hosted vs self‑hosted; base vs fine‑tuned/LoRA)
- **Selection criteria:** accuracy, latency, cost, context, policy support, locality.
- **Routing plan:** when to call which model? (by task/domain/guardrail)
- **Fallbacks & outage plan:** provider failover; “degraded but safe” mode.
- **Reproducibility:** temperature, seeds, sampling strategy, determinism needs.

---

## 4) Prompts, Policies, and Formats

- **System policy:** tone, persona, boundaries, confidentiality rules.
- **Canonical instruction set:** reusable snippets/prompt library entries.
- **Output contracts:** JSON Schema / TypeScript types that _must_ be produced.
- **Constrained decoding:** schema‑guided / tool‑required outputs? (yes/no)
- **Red‑team prompts to defend against:** (injection, jailbreaks, spec‑mismatch)

---

## 5) Tools, Functions, and Permissions

- **Tool catalogue:** name, inputs, outputs, side‑effects, auth, rate limits.
- **Least privilege:** which agent can call what and when? (RBAC/ABAC)
- **Idempotency & retries:** how to avoid double‑spend or duplicate effects.
- **Transactionality:** saga/compensation strategy across multi‑step actions.
- **Offline/long‑running tasks:** queues, timeouts, progress callbacks.

---

## 6) Knowledge, Retrieval, and Freshness (RAG if applicable)

- **Authoritative sources:** repos, DBs, APIs, files; owners & SLAs.
- **Indexing:** chunking rules, embeddings, metadata, multi‑tenant boundaries.
- **Freshness policy:** update cadence, invalidation, backfill on failure.
- **Citations & provenance:** must the agent cite sources? required fields.
- **Grounding checks:** how we detect/penalise hallucinations.

---

## 7) Data Governance & Privacy

- **Data classes:** PII/sensitive/special‑category; residency restrictions.
- **Prompt/response handling:** logging policy, redaction, retention windows.
- **Tenant isolation:** boundaries, encryption, access reviews.
- **Training/fine‑tune policy:** allowed datasets, licences, consent, opt‑outs.
- **SBOM/licensing for datasets/models:** SPDX/CycloneDX notes if relevant.

---

## 8) Quality & Evaluation

- **Offline evals:** datasets, metrics (exact match/F1/ROUGE/BLEU/BERTScore), thresholds.
- **Safety evals:** toxicity, bias, prompt‑injection resistance, jailbreak suites.
- **Task‑success evals:** pass@k, success@1, regression thresholds.
- **Online evals:** A/B or interleaving; guardrail monitors; user‑rated quality.
- **Approval tests:** golden transcripts that must not regress.

---

## 9) Safety, Abuse, and Policy

- **Content policy:** what to block/warn/allow; escalation routes.
- **Abuse scenarios:** prompt injection, data exfiltration, phishing, social engineering.
- **Policy stack:** safety filters, allow/deny lists, sensitive topics.
- **Rate‑limiting & anomaly detection:** per user/tenant/model/tool.
- **Incident playbooks:** containment, comms, retrospective, model rollbacks.

---

## 10) Observability for AI Systems

- **Telemetry:** prompt/response traces, tool calls, model route chosen.
- **Privacy‑safe logging:** what’s scrubbed, hashed, or dropped.
- **Dashboards:** quality, safety hits, cost, latency, cache hit rate.
- **Alerting:** thresholds for failure modes (hallucination spikes, tool error bursts).
- **Explainers:** how we’ll debug a bad answer (replayable sessions, seeds).

---

## 11) Performance, Cost, and Caching

- **Latency budgets:** p50/p95 per task, and end‑to‑end.
- **Throughput & concurrency:** expected QPS, burst factors.
- **Token/cost budgets:** per task/session; monthly cap; cost guardrails.
- **Caching:** embedding cache, response cache, KV TTLs; cache‑keys & invalidation.
- **Batching & streaming:** where applicable to cut cost/latency.

---

## 12) UX, Disclosure, and Controls

- **AI disclosure copy:** when/how users are told they’re interacting with AI.
- **User controls:** confidence hints, “show sources”, “try again”, “send for review”.
- **Failure UX:** safe, humble fallbacks; crisp error messages; recovery affordances.
- **Accessibility:** a11y for chat/assistants; readable transcripts; keyboard flows.

---

## 13) Delivery, Runtime, and Rollout

- **Environments:** dev/stage/prod parity; test fixtures for agents.
- **Feature flags:** gradual exposure; kill‑switches; targeting by tenant/role.
- **Blue/green & canary:** success criteria; automated rollback.
- **SecOps hooks:** secrets mgmt, key rotation, egress controls.
- **Compliance gates:** sign‑offs needed before public exposure.

---

## 14) Risks & Reversibility

- **Top risks (ranked):** model drift, vendor lock‑in, privacy breach, safety failure, cost blow‑out.
- **Mitigations:** model‑router, self‑host fallback, rate caps, red‑team budget.
- **Reversible decisions:** what can we change in <1 week?
- **Irreversible bets:** what needs an ADR + exec sign‑off?

---

## 15) Open Questions → Spikes/ADRs

- **Unknowns:** list and assign owners/dates.
- **Experiments:** what we’ll prototype, how we’ll measure, stop/go criteria.
- **Decisions pending:** link to ADR backlog with due dates.

---

### Appendices

#### A) Task Spec Template

- **Task:** one verb + object.
- **Inputs → Outputs:** types and schema.
- **Tooling needed:** functions + permissions.
- **Quality bar:** deterministic checks, acceptance tests.
- **Latency/cost targets:** p95 ms; tokens/task.
- **Safety notes:** policy flags, HITL, escalation.

#### B) Model Card Fields (per model)

- **Intended use / out‑of‑scope**
- **Data & training notes / licences**
- **Metrics (overall & subgroup)**
- **Known failure modes & mitigations**
- **Update cadence & deprecation plan**

#### C) Guardrail Matrix

| Risk             | Prevent                        | Detect            | Respond              |
| ---------------- | ------------------------------ | ----------------- | -------------------- |
| Hallucination    | Grounding, schema constraints  | Eval monitors     | Fall back / HITL     |
| Prompt injection | Input filters, tool whitelists | Pattern detectors | Kill‑switch, audit   |
| PII leakage      | Redaction, policies            | Scanners          | Scrub, rotate keys   |
| Cost blow‑out    | Budgets, caching               | Spend alerts      | Throttle, swap model |

---

**House style:** Be precise, cite sources when grounding answers, and prefer reversible designs. **If it’s risky, it gets a guardrail.**
