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

- [x] Resolve merge markers in `n00plicate/README.md` to align toolchain badges with Node 25.2.1 / pnpm 10.23.0.
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
