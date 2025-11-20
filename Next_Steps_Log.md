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
