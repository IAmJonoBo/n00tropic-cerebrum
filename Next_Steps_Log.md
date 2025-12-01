# Next Steps Log

## 2025-11-19 (branch: work, pr: N/A, actor: codex)

- [x] Restore pnpm workspace install (pnpm install → ERR_PNPM_WORKSPACE_PKG_NOT_FOUND for @n00plicate/design-tokens)
  - notes: added the missing `@n00plicate/*` workspace packages with source, tests, and tsconfig scaffolding so pnpm install/test/build chains resolve again.
  - checks: tests=pass, lint=pass, type=pass, sec=warn (mcp GHSA findings), build=pass

## 2025-11-20 (branch: work, pr: N/A, actor: codex)

- [x] Restore pnpm workspace install (use `scripts/bootstrap-workspace.sh` to init submodules then run `pnpm install`)
  - notes: carried forward install guidance after completing submodule bootstrap and workspace install setup.
  - checks: tests=unknown, lint=unknown, type=unknown, sec=unknown, build=unknown
- [x] Authenticate and sync required submodules (script now supports `GH_SUBMODULE_TOKEN` + `git submodule update --init --recursive`)
  - notes: submodules initialized and authentication guidance documented for reuse.
  - checks: tests=unknown, lint=unknown, type=unknown, sec=unknown, build=unknown
- [x] Add CODEOWNERS coverage for workspace root paths touched in this change
  - notes: ensured ownership mapping for root paths was documented after CODEOWNERS updates.
  - checks: tests=unknown, lint=unknown, type=unknown, sec=unknown, build=unknown

## 2025-11-21 status update (actor: Codex)

- [ ] Track upstream packages blocking deprecated-subdependency cleanup
  - notes: Context: working directly on `main` with no open pull request. Remaining warnings map to packages that are already on their latest releases:
    - Antora 3.1.14 → `@asciidoctor/core` → `asciidoctor-opal-runtime` keeps `glob@7.1.3`, `inflight@1.0.6`, `rimraf@2/3`, and `@babel/plugin-proposal-object-rest-spread@7.20.7`.
    - Loki 0.35.1 targets (`@loki/target-*`) depend on `aws-sdk@2.1692.0`, `gm@1.25.1`, `querystring@0.2.0`, `uuid@3.4.0`, and `@ferocia-oss/osnap@1.3.5` (which also brings `tempfile@3.0.0`).
    - Madge 8.0.0 → `dependency-tree@11.2.0` → `module-lookup-amd@9.0.5` continues to install `glob@7.2.3`.
  - checks: tests=not-run, lint=not-run, type=not-run, sec=warn (upstream issues), build=not-run

## 2025-11-23 (branch: main, actor: Codex)

- [x] Resolve merge markers in `n00plicate/README.md` to align toolchain badges with Node 24.11.1 / pnpm 10.23.0.
  - notes: conflict markers removed; file now clean for downstream docs/site renders.
  - checks: not required (docs-only).
- [x] Bootstrap `n00menon` as a runnable TS package with tests.
  - notes: added `package.json`, `vitest.config.ts`, README, refreshed `pnpm-lock.yaml`, and kept `tsconfig` on Node 24 profile.
  - checks: `pnpm -C n00menon test` (pass).

## 2025-11-23 (branch: main, actor: Codex)

- [x] Restore workspace pnpm install and sanitize npm vulnerabilities
  - notes: ran `scripts/setup-pnpm.sh` + `pnpm install`, added pnpm overrides for `esbuild@0.25.0`, `fast-json-patch@3.1.1`, and `tmp@0.2.4` to close OSV findings; reran `osv-scanner --config osv-scanner.toml .` (clean).
  - checks: osv-scanner=clean; biome scripts=pass.
- [x] Regenerate workspace health artifact
  - notes: `.dev/automation/scripts/workspace-health.py --publish-artifact` recorded clean state across submodules.
- [x] Stabilize Trunk bootstrap across subrepos
  - notes: added `scripts/trunk-upgrade-workspace.sh` (wraps trunk upgrade + config sync + optional checks), exported git metadata in `run-trunk-subrepos.sh`, pinned trunk runtimes in canonical config; trunk checks now pass across all subrepos.
  - checks: `TRUNK_BIN=/usr/local/bin/trunk .dev/automation/scripts/run-trunk-subrepos.sh` (pass).

## 2025-11-29 (branch: main, actor: Codex)

- [x] Added edge scaffolds (RPi/Jetson) with FastAPI + llama.cpp/ONNX, manifest wiring, and trunk-clean renders via `nox -s validate_templates_all -- --template edge-rpi --template edge-jetson`.
- [x] Extended guardrail/workflow schemas + agent registry; wired agent-core routing for edge models and MPC federation bridges.
- [x] Introduced GuardrailExecutor, telemetry hooks, and meta-learner stubs in n00-school; A/B harness appended to evaluation utilities.

## 2025-11-29 backlog (actor: Codex)

- [ ] Execute `job-frontiers-evergreen-ssot` workstreams (docs charter,
      automation hooks, template expansion, telemetry, generator contracts)
      so n00-frontiers remains the canonical SSoT. Tracked via ADR-008 and
      the new horizons job directory.

## 2025-11-30 (branch: main, actor: Codex)

- [x] Push agent-core coverage and CLI QA
  - notes: Added targeted tests for model router scoring/circuit paths, tag registry/CLI analytics, unified telemetry propagation/OTEL stubs, and planning workflow phases. Coverage lifted to ~77% (from ~53%); next push targets tracing/unified_telemetry/model_router deep branches to reach the 85% policy bar.
  - checks: `python -m pytest` in `n00t/packages/agent-core` (pass, coverage ~77%); `pnpm -C n00t run test` (pass, vitest suite).
  - follow-ups: add tracing branch coverage, exporter/propagator edge cases, and record the next run in `.dev/automation/artifacts/automation/agent-runs.json`.

## 2025-12-01 (branch: main, actor: Codex)

- [x] Edge/guardrail observability + workflow compiler
  - notes: Added guardrail/routing OTEL spans in `observability.py` and `observability-node.mjs`; stubbed edge dashboard at `artifacts/telemetry/edge-dashboard.json`. Delivered workflow compiler + CLI (`n00tropic_cli design workflow compile`) that validates Cortex DSL, emits agent configs, run script, and telemetry hints.
  - checks: meta-check full suite (frontiers sanity, cortex schemas/ingest, n00-school pytest, n00t lint/test/build) all ✅; manual `pnpm -C n00t run test` ✅; n00-school pytest ✅.
  - follow-ups: finish workspace-release dry-run once cross-repo consistency completes; wire compiler output registration into `n00t/capabilities/manifest.json` in a subsequent pass if required by orchestrations.
