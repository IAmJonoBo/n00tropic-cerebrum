---
id: doc-workspace-skeleton-migration
title: Workspace Skeleton Migration Plan
lifecycle_stage: deliver
status: reference
owner: platform-ops
review_date: 31-03-2026
tags:
  - governance/project-management
  - automation/n00t
links:
  - type: runbook
    path: ../n00t/START HERE/PROJECT_ORCHESTRATION.md
  - type: template
    path: ../.dev/automation/workspace-skeleton.yaml
---

# Workspace Skeleton Migration Plan

This plan threads the enforced repo skeleton + CLI/venv standards across the polyrepo. Use it to roll changes methodically and audit compliance.

## Target state

- `.dev/automation/workspace-skeleton.yaml` defines required dirs per repo (cli/, scripts/, env/, tests/, artifacts/, automation/, docs, toolchain/.dev/<repo>/scripts where applicable).
- `check-workspace-skeleton.py` auto-creates missing dirs (+ .gitkeep) or reports deviations; wired into `cli.py doctor`.
- `cli.py` exposes `repo-context` and writes `artifacts/workspace-repo-context.json` with lang/pkg/venv/cli metadata per subrepo.
- Each repo has:
  - `cli/main.py` (or `cli/index.ts`) thin wrapper to shared scripts (commands: bootstrap, lint, verify-artifacts, publish).
  - Deterministic venv (`.venv-<repo>` for Python) + bootstrap script.
  - `tooling/` (or `infra/`) for Docker/devcontainer/runtime manifests.
  - `docs/architecture.md` with dependency surface + CLI entrypoints + directory contract.

## Rollout steps (repeat per repo)

1) **Skeleton enforcement**
   - Run `python3 .dev/automation/scripts/check-workspace-skeleton.py --apply`.
   - Add `.gitkeep` for empty required dirs.
2) **CLI shim**
   - Add `cli/main.py` (Python) or `cli/index.ts` (Node) delegating to shared scripts with commands: `bootstrap`, `lint`, `verify-artifacts`, `publish`.
   - Ensure callable via repo-local env (`.venv-<repo>` or `pnpm exec`).
3) **Venv bootstrap**
   - Add `bootstrap-python.sh` (or repo-specific variant) that creates `.venv-<repo>`, installs `requirements.txt` / `requirements-dev.txt`.
   - Update root `cli.py` to support `python cli.py <repo> bootstrap` (stub to follow once per-repo scripts exist).
4) **Tooling dir**
   - Create `tooling/` (or `infra/`) with Dockerfiles/devcontainers/runtime manifests; ensure `toolchain-manifest.json` can ingest paths.
5) **Docs**
   - Add `docs/architecture.md` capturing dependency surface, CLI commands, directory contract; cross-link via Antora where applicable.
6) **Automation symmetry**
   - Host repo-specific steps under `.dev/<repo>/scripts/` and publish entrypoints in the workspace script index.
   - Root automation should call `pnpm exec <repo-cli> ...` instead of ad-hoc shell paths.
7) **Release gate**
   - Update `workspace-release.sh` to run `check-workspace-skeleton.py` and fail if missing paths.

## Audit cadence

- Run `python3 cli.py doctor --strict` (once tsx/agent deps are installed) to surface skeleton deviations and regenerate `workspace-repo-context.json`.
- Track compliance per repo in PR templates until all shims/venvs/docs are in place.
