# Trunk CI Playbook

This workspace keeps Trunk for developer ergonomics, but we lean on system runtimes and CI caching rather than hermetic downloads.

> **Note:** The repository no longer ships a top-level `.trunk/` directory. Canonical Trunk configs live under `n00-cortex/data/trunk/base/.trunk/` and the individual subrepositories. Runners should copy/overlay those configs into place (for example via `scripts/sync-trunk-defs.mjs` or subrepo-specific automation) before invoking the CLI.

## Sourcing configuration

1. Update `n00-cortex/data/trunk/base/.trunk/trunk.yaml` when policy changes are required.
2. Run `scripts/sync-trunk-defs.mjs` (or `.dev/automation/scripts/run-trunk-subrepos.sh --sync-only`) so subrepos receive the refreshed definitions.
3. Ensure CI creates a writable cache location (for example `~/.cache/trunk`) and symlinks/copies the canonical config into each repo that still depends on Trunk.
4. Set `TRUNK_BIN` (or add Trunk to `PATH`) on runners because there is no repo-local launcher anymore.

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
