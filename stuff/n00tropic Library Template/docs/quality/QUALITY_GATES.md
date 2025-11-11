# Quality Gates (CI must pass)

- Linting: 0 errors.
- Tests: 100% passing; coverage ≥ target.
- Static analysis: no new high/critical issues.
- Secrets scan: 0 leaks.
- Bundle size/perf budgets (if applicable): within thresholds.

Fail the build if any gate fails. No “just this once”.
