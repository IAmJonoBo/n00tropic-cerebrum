# Architecture Overview

## Snapshot (C4)

- **Context**: actors & neighbouring systems.
- **Containers**: runtime units (services, UIs, jobs), tech choices.
- **Components**: key internals of each container.
- **Trust boundaries**: where authN/Z, encryption, and validations must hold.

> C4 reference: https://c4model.com (use context → containers → components as needed).

## Key flows

- Primary user journey: …
- Critical background job: …

## Quality attributes (and how we hit them)

- Performance: budgets, expected load, bottlenecks, caching strategy.
- Availability/resilience: patterns (circuit‑breakers, retries, idempotency).
- Security: data classes, boundary checks, secrets posture.
- Observability: logs/metrics/traces, dashboards.

## Interfaces

- External APIs (OpenAPI / GraphQL): links to specs.
- Events: topics, schemas, delivery guarantees.

## Open decisions

- See `/docs/architecture/ADRs`.
