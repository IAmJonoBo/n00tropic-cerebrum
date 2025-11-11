# Test Strategy

- **Unit:** fast, deterministic, mock externalities.
- **Integration:** real boundaries (DB, queues, HTTP), contract tests.
- **E2E/UI:** key flows only; avoid flaky nightmares.
- **Property/Fuzz:** for parsers/transformers.
- **Security:** SAST/DAST/dep scan; secrets detection.
- **Performance:** latency/throughput under load; budgets & SLOs.

Coverage: aim high where it matters; never ship untested core logic.
