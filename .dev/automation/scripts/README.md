# Automation scripts (canonical entry points)

- `meta-check.sh`: umbrella health check for the superrepo (used in CI).
- `check-cross-repo-consistency.py`: enforces toolchain pins and template/workflow drift.
- `trunk-manage.sh`: single entry for Trunk ops (sync check/pull/push, upgrade, fmt via run-trunk-subrepos).
- `sync-trunk.py`: canonical Trunk config sync; invoked by `trunk-manage.sh`.
- `run-trunk-subrepos.sh`: Trunk fmt/check across subrepos (used by workspace-health, wrapped by `trunk-manage.sh fmt`).
- `sync-trunk-autopush.py`: CI helper to apply Trunk config changes automatically (still valid).
- `workspace-health.sh` / `workspace-health.py`: high-level workspace gate.
- `wrangle-branches.sh` / `tmp-branch-audit.sh`: branch hygiene utilities; consolidate here as the entry point.
- `normalize-workspace-pnpm.sh`: normalizes pnpm store/config for runners.
- `sync-nvmrc.sh`: links subrepos back to the workspace `.nvmrc` so Node bumps propagate automatically (skip overrides like `n00tropic` unless `--force`).
- `plan-exec.sh`: execute plan templates for automation runs.
- `doctor.sh`: workspace doctor (tokens, Trunk, dashboards).
- `generate-renovate-dashboard.py`: snapshot Renovate dependency dashboards.

Deprecated wrappers (prefer the entries above):

- `sync-trunk-configs.sh`, `trunk-upgrade.sh`, `sync-trunk-defs.mjs`: use `trunk-manage.sh` instead.
- Redundant branch scripts should route through `wrangle-branches.sh`.
