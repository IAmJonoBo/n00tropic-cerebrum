# n00tropic Discovery Questionnaire

_Witty, intelligent, and frank. We build frontier-grade software and agent tooling. Let’s ask what matters and skip the fluff._

> **How to use:** Fill this once per project during Discovery. Answers feed directly into the docs scaffold: Project Charter, PRD, Architecture Overview (C4), ADRs, Security/Privacy, AI Guardrails/Evals, Test Strategy, CI/CD, Observability, and Release process. Keep it crisp; link artefacts when useful.

---

## 0) Executive Snapshot (one-pager)

- **Working title:**
- **Problem worth solving (150 chars):**
- **Primary users / beneficiaries:**
- **Success criteria (3–5 measurable outcomes):**
- **Must-haves / Non-negotiables:**
- **Known constraints (legal, data, runtime, platform):**
- **Initial risks (top 3) & how we’ll learn fast:**
- **Decision cadence:** Who signs off, when?

---

## 1) Context & Stakeholders

- **Vision in one paragraph:**
- **Business objectives & KPIs:**
- **Stakeholders & roles (RACI snapshot):**
- **Adjacent systems / programmes impacted:**
- **Assumptions to validate early:**

---

## 2) Users, Jobs, and UX

- **User groups & primary jobs-to-be-done:**
- **Top tasks / flows to nail (ranked):**
- **Accessibility needs (WCAG):**
- **Locales, content tone, and disclosure (when AI is involved):**
- **UX constraints (brand, design system, device classes):**

---

## 3) Functional Scope (PRD seeds)

- **User stories with acceptance criteria (link to backlog):**
- **Out-of-scope (explicitly):**
- **Hidden complexity hotspots:** parsers, schema transforms, long-running workflows, data joins, etc.
- **Migration/compatibility expectations:** (if replacing an existing system)

---

## 4) Non‑Functional Requirements

- **Reliability targets (SLIs/SLOs):** latency, availability, error rates; by key journey.
- **Performance budgets:** page/app size, cold start, p95/p99 latency, throughput, concurrency.
- **Capacity expectations:** users, data volume, peak factors, growth.
- **Security baseline:** authN/Z, secrets, input validation, platform hardening.
- **Privacy baseline:** data classes (PII/sensitive), retention, deletion workflows, lawful basis.
- **Compliance:** e.g., GDPR/POPIA, PCI DSS, SOC 2, sectoral regs.

---

## 5) Data, Schemas, and Integrations

- **Authoritative data sources & ownership:**
- **Domain model / key entities & invariants:**
- **Data schemas & contracts:** link OpenAPI/GraphQL/AsyncAPI, DB schemas.
- **Data quality, lineage, and provenance expectations:**
- **Sync/async integrations, events, and delivery guarantees:**
- **Data retention & minimisation policy:**

---

## 6) Architecture Overview (C4 seeds)

- **Context diagram actors & neighbouring systems:**
- **Containers (runtime units) & primary tech options:**
- **Components (high-level), boundaries, and trust zones:**
- **Cross-cutting concerns:** caching, idempotency, retries, feature flags, i18n, a11y.
- **Decisions needed soon → ADRs backlog:**

---

## 7) Security & Privacy (Threat Models)

- **Security threats (STRIDE) at key boundaries:**
- **Privacy threats (LINDDUN):** link data flows with mitigations.
- **Verification standard:** ASVS level/controls to target, secrets policy, SBOM plan (SPDX/CycloneDX).
- **Identity & access:** authN methods, SSO/OIDC, roles/claims, least privilege.
- **Data protection:** encryption at rest/in transit, key management, backups, DLP.
- **Responsible disclosure & logging of security events:**

---

## 8) AI / Agent Design (first-class)

- **Where agents help:** coding, UX, retrieval, orchestration, decisioning, testing.
- **Agent roles & tools:** orchestrator vs workers; tool names, inputs/outputs, permissions.
- **Model choices:** vendor/open, versions, token/cost budgets, latency SLAs.
- **Safety & guardrails:** prompt hygiene, red-teaming, content policy, abuse/PII filters, human-in-the-loop.
- **Evaluation plan:** metrics (quality, safety, bias), offline datasets, online checks, regression gates.
- **Model cards (per model):** intended use, limitations, risks, dataset notes, eval results.
- **Data boundaries:** what never leaves the tenant/project; RAG sources and freshness policies.

---

## 9) DevEx, Toolchain, and Repo Conventions

- **Languages & frameworks under consideration (justify per use):**
- **Package managers, build tools, monorepo/multi, workspace layout:**
- **Developer environment:** required runtimes, containers, scripts, pre-commit hooks.
- **Coding standards:** style guides, naming, error taxonomy, logging norms.
- **Commit & PR discipline:** Conventional Commits, small PRs, mandatory checklists.

> _Tech choices come **after** discovery. Capture constraints and evaluation criteria here; decide with ADRs._

---

## 10) Testing, Quality Gates, and CI/CD

- **Test strategy:** unit, integration, E2E, contract, property/fuzz, performance, security.
- **Coverage targets & critical-path coverage:**
- **Static analysis & linters (must pass):**
- **Secrets detection & dep scanning:**
- **CI stages & required checks:** build, test, scans, SBOM, artifacts.
- **CD strategy:** environments, approvals, feature flags, canary/blue‑green, rollback drills.

---

## 11) Observability & Ops

- **Golden signals & SLIs per journey:** latency, traffic, errors, saturation.
- **Metrics, logs (structured), and traces:** where, retention, PII scrubbing.
- **Dashboards & alerts:** who gets paged, burn-rate alerts, runbooks.
- **Backups, DR, and resilience:** RPO/RTO, chaos drills.
- **Incident response:** severity matrix, comms, post‑mortems (blameless), action tracking.

---

## 12) OSS, Licensing, and Community

- **License (default MIT unless specified) and third‑party obligations:**
- **Contribution model:** governance, maintainer policy, issue/PR templates.
- **Security.md & disclosure channel:**
- **Public roadmap/comms expectations:**

---

## 13) Delivery Plan & Risks

- **Milestones & release plan:**
- **Resourcing & skills:** in-house, partner, community, agents.
- **Top risks & mitigations:** technical, privacy, operational, vendor, lock‑in.
- **Exit ramps & reversibility:** how we back out of big choices.

---

## 14) Admin

- **Owner (product + tech):**
- **Decision forum / schedule:**
- **Document links:** Charter, PRD, C4 diagrams, ADRs, Risk Register, Threat Model, Test Strategy, AI Eval Plan.

---

### Appendices

#### A. SLO Template (by journey)

- **User journey:**
- **SLIs:** availability %, p95 latency, error rate, etc.
- **SLO targets & windows:** e.g., 99.9% over 28 days.
- **Error budget:** 1 − SLO; alert on burn‑rate ≥ X over Y.
- **Dashboards & alert policy links:**

#### B. Performance Budget Template

- **Budgets:** JS/CSS payload (kB), image budget, app bundle size, cold start, p95/p99 latency, Lighthouse thresholds.
- **Enforcement:** CI budget check, page‑weight alarms, perf CI job.

#### C. Threat Modeling Checklist

- **STRIDE:** spoofing, tampering, repudiation, info disclosure, DoS, privilege escalation.
- **LINDDUN:** linking, identification, non‑repudiation, detectability, disclosure, unawareness, non‑compliance.
- **Mitigation mapping:** controls per threat; acceptance or remediation plan.

#### D. AI Guardrails & Model Card Prompts

- **Guardrails:** policy list, block/allow, escalation steps, red‑team suite, prompt hygiene.
- **Model card fields:** intended use/out‑of‑scope, datasets, metrics (overall & subgroup), risks/harms, limitations, update cadence.

---

**House style:** Candid > vague. Measurable > hand‑wavy. Reversible > rigid.  
**Default posture:** OSS‑first, cloud‑optional, DX‑obsessed, forever‑green.
