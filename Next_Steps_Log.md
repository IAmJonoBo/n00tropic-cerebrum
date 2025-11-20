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
