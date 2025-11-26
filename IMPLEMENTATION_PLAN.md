# Dependency Management Stack – Implementation Plan

**Date:** 2025-11-26

## Discovery (workspace snapshot)

- Package managers in play: pnpm monorepo (`pnpm-workspace.yaml`), multiple Python repos using uv/venv locks (`requirements.workspace.*`), Rust crates (tauri + token orchestrator), Swift package (`Package.swift`), assorted Dockerfiles in templates.
- Existing dependency tooling: many `renovate.json` files extending `github>n00tropic/n00tropic-cerebrum//renovate-presets/workspace.json` or `local>renovate-presets/workspace.json`, but no preset exists at workspace root (only `n00-cortex/renovate-presets/workspace.json`). Renovate extends check/apply workflows already run (`.github/workflows/renovate-extends-*.yml`). No Dependabot configs.
- CI: Actions workflows for docs, runners, trunk sync, toolchain health, but no SBOM/Syft or dependency-risk publishing. `osv-scanner.toml` present but unused in CI.
- Control surfaces: `cli.py` orchestrator plus MCP capability manifest (`n00t/capabilities/manifest.json`) mapping to `.dev/automation/scripts/`. Workspace manifest (`automation/workspace.manifest.json`) lists canonical repos/paths we can reuse as SBOM targets.

## Target architecture

- **Renovate**: Single canonical preset under `renovate-presets/` at repo root with opinionated grouping, schedules, and ecosystem coverage (pnpm, Python/uv, Cargo, SwiftPM, GitHub Actions). Root `renovate.json` extends it; subrepos/templates extend the GitHub-hosted preset for consistency. Keep existing extend-check/apply workflows.
- **SBOM (Syft)**: Scriptable generator (`.dev/automation/scripts/deps-sbom.sh`) that walks targets from `automation/workspace.manifest.json`, emits CycloneDX JSON into `artifacts/sbom/<repo>/<ref>/`. GitHub Actions workflow `.github/workflows/sbom.yml` runs on `main` and tags, storing artefacts.
- **Dependency-Track**: Ops bundle under `ops/dependency-track/` with Docker Compose + README. SBOM workflow optionally uploads BOMs via `DEPENDENCY_TRACK_BASE_URL` + `DEPENDENCY_TRACK_API_KEY`, tagging components as `n00tropic-cerebrum::<repo>`.
- **Control / MCP**: CLI subcommands (`deps:sbom`, `deps:audit`, `deps:renovate:dry-run`) wrap the scripts; MCP capability entries expose the same operations for agents. Docs consolidated in `docs/dependency-management.md` with `AGENT_HOOK: dependency-management` markers.

## Planned changes (incremental)

1. Add root `renovate-presets/` preset + refresh `renovate.json` + align subrepo/template extends; document migration and keep existing package rules.
2. Ship Syft helper script + SBOM workflow + deterministic output layout; cache syft install and reuse workspace manifest targets.
3. Scaffold Dependency-Track deployment bundle and wire SBOM workflow upload path + tagging convention.
4. Extend CLI + MCP capabilities to trigger SBOM generation, uploads, and Renovate dry-runs; surface logs/paths for agents.
5. Write `docs/dependency-management.md` summarising usage, secrets, and troubleshooting; note retired/redirected configs if any.
6. Add drift/deprecation detection (`deps-drift`) to remediate mismatches and recommend replacements; emit CI artifact via deps-drift workflow.

Risks/notes: ensure syft excludes `node_modules`/`.venv` for speed; Dependency-Track upload guarded by secrets so workflow remains dry when unset; keep Renovate schedules conservative to avoid noise.
