# Next Steps

## Tasks
- [ ] Restore `pnpm exec antora antora-playbook.yml` (fails because https://github.com/IAmJonoBo/n00-cerebrum.git requires credentials). (owner: codex, due: 2025-11-30)
- [ ] Reduce the workspace Vale backlog so `make validate` succeeds (81 errors across legacy docs, see chunk 90691d). (owner: codex, due: 2025-12-15)
- [ ] Mirror the Antora/Vale/Lychee workflow plus Markdown→AsciiDoc migration across every repo listed in `docs/modules/ROOT/pages/migration-status.adoc` once access to submodules is available. (owner: codex, due: 2025-12-31)
- [ ] Add SBOM generation (CycloneDX or SPDX) to CI and document the local command to meet the baseline requirement. (owner: codex, due: 2025-12-15)
- [ ] Define CODEOWNERS + branch protection for docs/tooling paths so reviews are enforced. (owner: codex, due: 2025-12-05)

## Steps
1. Secure read access (or cached mirrors) for each content repo referenced in `antora-playbook.yml` so local builds do not fail.
2. Establish a Vale remediation plan (prioritised by nav area) and land follow-up PRs to bring `make validate` back to green.
3. Initialize each sibling repo (n00-frontiers, n00-cortex, etc.), run `scripts/convert-md-to-adoc.sh`, and mirror the docs CI from `stuff/Temp/temp-doc-2.md`.
4. Integrate SBOM generation into CI and provide a documented local command for developers.

## Deliverables
- Passing Antora build logs
- Workspace-wide Vale + Lychee reports
- PRs per repo covering Antora migration + CI sync
- SBOM artifact instructions / workflow updates

## Quality Gates
- tests: pass
- linters/formatters: clean
- type-checks: clean
- security scan: clean
- coverage: ≥ current baseline
- build: success
- docs updated

## Links
- PRs: pending
- Files/lines: pending

## Risks/Notes
- Remote content repos are private; Antora builds fail without cached sources. (`pnpm exec antora antora-playbook.yml` → chunk c339f3)
- `make validate` now runs Vale/Lychee locally but still fails because of legacy backlog (chunk 90691d).
- SBOM generation has not been implemented anywhere in the workspace yet.
