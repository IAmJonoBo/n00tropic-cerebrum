# AI Evaluation Plan

## Metrics

- Quality: pass@k, task success rate, regression deltas.
- Safety: hallucination rate, policy violations.
- Efficiency: latency, token/cost budgets.

## Datasets & protocol

- Gold‑set curation, periodic refresh, holdout policy.
- Review cadence and sign‑off gates before release.

## Automation

- CI job to run eval suites; block on regressions beyond threshold.
