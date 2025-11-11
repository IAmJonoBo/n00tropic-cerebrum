# CI Pipeline

**Stages:** lint → typecheck → test → build → security scans → package → (optional) E2E → publish.

- Cache dependencies sensibly; kill flakiness fast.
- Parallelise where possible; keep feedback under 10 minutes.
- Generate SBOM; upload coverage & reports.
