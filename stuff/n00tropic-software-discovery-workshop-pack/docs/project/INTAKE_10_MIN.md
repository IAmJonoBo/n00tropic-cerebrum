# n00tropic — Discovery Intake (10 minutes)

_Witty, intelligent, frank. This is the pre‑kickoff sanity scan for any software/web project._

> **Outcome:** enough signal to approve a deep‑dive or hit pause. Leave blanks rather than guessing. Link artefacts where useful.

## 0) One‑liner & who it’s for

- **Working title:**
- **Elevator pitch (one sentence):**
- **Primary users / beneficiaries (ranked):**

## 1) Outcomes & must‑nots

- **Top 3 measurable outcomes:**
- **Non‑negotiables:** _(security, privacy, compliance, SLOs, cost, accessibility)_

## 2) Scope & constraints

- **In‑scope (top 5 capabilities):**
- **Out‑of‑scope (explicitly):**
- **Constraints:** _legal, data, platform, runtime, procurement_

## 3) Users, jobs, and UX

- **Key jobs‑to‑be‑done (3–5):**
- **Top tasks/flows to nail:**
- **Accessibility/localisation needs:**

## 4) Architecture snapshot

- **Neighbours & integrations:** _systems we touch; data directions_
- **Runtime units (containers/services/jobs):**
- **Trust boundaries:** _authN/Z, encryption, validation_

## 5) Data & contracts

- **Authoritative sources & ownership:**
- **Schemas & APIs:** _OpenAPI/GraphQL/AsyncAPI links_
- **Retention & lineage expectations:**

## 6) NFRs (non‑functional requirements)

- **Reliability targets (SLIs/SLOs):** availability, latency, error rates.
- **Performance budgets:** payload size, p95/p99 latency, throughput.
- **Capacity:** users, data volume, burst factor, growth.
- **Security & privacy baseline:** _ASVS level, PII classes, residency_
- **Compliance:** _GDPR/POPIA, PCI DSS, SOC 2, etc._

## 7) DevEx & toolchain

- **Evaluation criteria for stack (post‑discovery):** _DX, maintainability, ecosystem, portability_
- **Repo layout & conventions:** _monorepo vs multi; scripts; hooks_
- **Pre‑commit quality hooks:** _format, lint, typecheck, secrets scan_

## 8) Testing, quality gates, CI/CD

- **Test types:** _unit, integration, E2E, contract, performance, security_
- **Coverage targets:** _critical paths identified_
- **Quality gates:** _lint/static analysis, coverage floors, bundle/perf budgets_
- **CI stages:** _build, test, scans, artifacts, SBOM_
- **Release:** _envs, flags, canary/blue‑green, rollback drills_

## 9) Observability & ops

- **SLIs per key journey:**
- **Logs/metrics/traces:** _where, retention, PII scrubbing_
- **Dashboards & alerts:** _owners & thresholds_
- **Backups/DR:** _RPO/RTO, drills_

## 10) Risks & reversibility

- **Top risks (ranked):**
- **Reversible vs irreversible decisions:**
- **Spikes next (≤ 1 week each): owners & dates:**

> If you can’t fill 50% of this, you’re not stuck — you’re honest. Run spikes, then do the deep‑dive.
