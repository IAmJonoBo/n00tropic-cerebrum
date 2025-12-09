# Trunk CI Playbook

This workspace keeps Trunk for developer ergonomics, but we lean on system runtimes and CI caching rather than hermetic downloads.

> **Note:** The repository no longer ships a top-level `.trunk/` directory. Canonical Trunk configs live under `n00-cortex/data/trunk/base/.trunk/` and the individual subrepositories. Runners should copy/overlay those configs into place (for example via `scripts/sync-trunk-defs.mjs` or subrepo-specific automation) before invoking the CLI.

> **Install policy:** `scripts/bootstrap-workspace.sh` now invokes `python3 cli.py trunk-upgrade` with `TRUNK_INSTALL=1` so that every freshly instantiated environment refreshes the Trunk CLI and plugins recursively. Set `SKIP_BOOTSTRAP_TRUNK_UPGRADE=1` if you intentionally want to skip this step; otherwise bootstrap will surface failures early so we never drift. Outside of the bootstrap path we still avoid silently installing Trunk—run `trunk upgrade --no-progress` (or `TRUNK_INSTALL=1 .dev/automation/scripts/trunk-upgrade.sh`) any time you need to refresh manually, and ensure CI/ephemeral runners keep `TRUNK_INSTALL=1` enabled.

## Bootstrap automation

The workspace bootstrap script now guarantees that Trunk stays aligned:

```bash
# Refresh submodules, hooks, runtimes, and Trunk everywhere
scripts/bootstrap-workspace.sh

# Skip the Trunk portion if you are already managing it elsewhere
SKIP_BOOTSTRAP_TRUNK_UPGRADE=1 scripts/bootstrap-workspace.sh
```

Because this hook calls into `python3 cli.py trunk-upgrade`, it walks every repository that ships a `.trunk/trunk.yaml` (including nested submodules) and applies the canonical upgrade sequence. Any failure bubbles up in the bootstrap log so you can fix the offending repo before starting real work.

## Smart upgrades & caching

- `.dev/automation/scripts/trunk-upgrade.sh` keeps a lightweight cache under `.dev/automation/artifacts/automation/trunk-upgrade-state.json`. When `TRUNK_UPGRADE_SMART=1` (bootstrap sets this by default) the script hashes each repository’s `.trunk/trunk.yaml` and only re-runs Trunk where the hash changed or the repo is new. Set `TRUNK_UPGRADE_FORCE_ALL=1` to bypass the heuristic.
- If no repositories changed since the last successful run, the script respects `TRUNK_UPGRADE_MAX_AGE` (default `86400` seconds). Within that window it skips the upgrade entirely; once the window expires it falls back to a full sweep so plugin bumps are still applied periodically.
- Force specific repos into the run even if their hashes are unchanged via `TRUNK_UPGRADE_ALWAYS_INCLUDE='["n00t","n00-frontiers"]'` (JSON list, comma/space-separated strings also work). This is handy while migrating a repo or debugging a flaky tool.
- Set `TRUNK_UPGRADE_JOBS` to run multiple repositories in parallel (defaults to `1`). The script collects output per repo, surfaces it once the job completes, and still records failures individually. Leave it at `1` for deterministic debugging; bump to `4`+ when you just want speed.
- The script exports `TRUNK_CACHE_ROOT` (defaults to `<workspace>/.cache/trunk`) so that every repo shares the same plugin downloads. Persist this directory between CI runs to avoid repeated downloads.
- We only record state for repos whose upgrade succeeded. If a repo fails, it will appear as “changed” again during the next smart run so failures are retried automatically.

Set `TRUNK_UPGRADE_SMART=0` (or run with `TRUNK_UPGRADE_FORCE_ALL=1`) whenever you need a belt-and-suspenders sweep—for example before releases or after bumping Trunk’s canonical configs. The heuristic simply saves time during day-to-day QA loops.

## Sourcing configuration

1. Update `n00-cortex/data/trunk/base/.trunk/trunk.yaml` when policy changes are required.
2. Run `scripts/sync-trunk-defs.mjs` (or `.dev/automation/scripts/run-trunk-subrepos.sh --sync-only`) so subrepos receive the refreshed definitions.
3. Ensure CI creates a writable cache location (for example `~/.cache/trunk`) and symlinks/copies the canonical config into each repo that still depends on Trunk.
4. Set `TRUNK_BIN` (or add Trunk to `PATH`) on runners because there is no repo-local launcher anymore.

### Auto-promote canonical configs

Running `.dev/automation/scripts/sync-trunk-configs.sh --check` now forwards `--auto-promote` to `sync-trunk.py`. When every downstream repo shares identical `.trunk/trunk.yaml` contents (the usual outcome after a repo-wide `trunk upgrade`), the helper automatically promotes that payload back into `n00-cortex/data/trunk/base/.trunk/trunk.yaml` instead of forcing a manual push/pull dance. Set `TRUNK_SYNC_AUTO_PROMOTE=0` if you need to opt out (for example while testing bespoke overrides). The flag is ignored whenever downstream copies differ, so individual repos can still pilot custom linters without being overwritten.

### Fan-out & PR automation

- Run `python3 cli.py trunk-sync` (or `.dev/automation/scripts/sync-trunk-autopush.py`) after `trunk-upgrade.sh` to check for drift, auto-promote uniform downstream payloads, and immediately fan them back out with `--pull`.
- The command writes a JSON status file (path echoed at the end) so you can inspect which repos drifted and whether a promotion occurred. When no drift is detected it exits early without touching the repos.
- Add `--repos n00-frontiers n00-cortex` to focus on a subset, or `--apply` to commit/push `.trunk/trunk.yaml` changes and open PRs automatically via `gh pr create`.
- `trunk-upgrade.sh` now runs with `TRUNK_POST_SYNC=1` by default, so every upgrade sweep automatically follows up with `sync-trunk-configs.sh --check --auto-promote`. Use `TRUNK_POST_SYNC=0` if you want to handle promotion manually.

## Runtimes

Trunk configuration (`n00-frontiers/.trunk/trunk.yaml`) allows the system Node.js, Python, and Go installs. Make sure your CI image already includes the versions declared in `n00-cortex/data/toolchain-manifest.json`.

```yaml
runtimes:
  enabled:
    - python
    - go
    - node
  definitions:
    - type: python
      system_version: allowed
    - type: go
      system_version: allowed
    - type: node
      system_version: allowed
```

With these settings the hermetic bootstrap script is a no-op (`scripts/bootstrap-trunk-python.sh`).

## Cache the CLI and results

Persist `~/.cache/trunk` so the CLI, plugins, and linters are reused between runs.

GitHub Actions

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/trunk
    key: ${{ runner.os }}-trunk-${{ hashFiles('**/.trunk/trunk.yaml') }}
    restore-keys: |
      ${{ runner.os }}-trunk-
```

GitLab CI

```yaml
cache:
  key: "trunk-${CI_RUNNER_EXECUTABLE_ARCH}"
  paths:
    - $HOME/.cache/trunk
```

## Command shape

- Pull requests: `trunk check --ci`
- Nightly/cron: `trunk check --all --ci`

The hold-the-line behaviour cuts runtime dramatically by touching only modified files on PRs.

## Environment variables

Trunk does not inherit the shell environment. If you need proxies or locales, define them in `.trunk/trunk.yaml`:

```yaml
lint:
  definitions:
    - name: eslint
      environment:
        - name: HTTP_PROXY
          value: ${HTTP_PROXY}
        - name: HTTPS_PROXY
          value: ${HTTPS_PROXY}
```

## When to consider alternatives

- **pre-commit** + **pre-commit.ci** – No local downloads, strong community support, integrates with git hooks.
- **Mega-Linter** – Containerized linter suite, good for locked-down environments, heavier on CI minutes.

Stick with Trunk if you can cache `~/.cache/trunk` and provide system runtimes; swap only if network policies forbid the necessary downloads.
