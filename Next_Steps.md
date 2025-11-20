# Next Steps

## Tasks
- [ ] Audit repos and migrate docs per instructions (owner: codex, due: 2025-02-05)
- [ ] Authenticate and sync required submodules (git submodule update --init --recursive prompts for GitHub credentials) (owner: codex)
- [ ] Add CODEOWNERS coverage for workspace root paths touched in this change (owner: codex)
- [ ] Remediate OSV scanner alerts for `mcp` (GHSA-3qhf-m339-9g5v, GHSA-j975-95f5-7wqh) in `mcp/docs_server/requirements.txt` (owner: codex)
- [ ] Restore superrepo sync (scripts/check-superrepo.sh exit 1; git submodule update --init --recursive prompts for GitHub credentials) (owner: codex)
- [ ] Repair workspace health sync (.dev/automation/scripts/workspace-health.sh --sync-submodules --json exit 1; artifacts/workspace-health.json missing) (owner: codex)
- [ ] Fix Python bootstrap (scripts/bootstrap-python.sh exit 1 missing n00tropic/requirements.txt; submodules unavailable) (owner: codex)
- [ ] Restore trunk automation (.dev/automation/scripts/run-trunk-subrepos.sh --fmt exit 1: missing scripts/sync-trunk-defs.mjs and trunk binary; curl -sSf https://trunk.io/install.sh | sh returned 404) (owner: codex)
- [ ] Resolve Biome script lint path (pnpm -s exec biome check "scripts/**/*.mjs" exit 1: path missing) (owner: codex)
- [ ] Repair Antora docs build (make docs exit 2: missing .git/modules/n00-frontiers; submodules not initialized) (owner: codex)

## Steps

- [ ] Audit repos and migrate docs per instructions (owner: codex, due: 2025-02-05)
- [ ] Mirror Antora/Vale/Lychee workflows + Markdown→AsciiDoc migrations across repos listed in `docs/modules/ROOT/pages/migration-status.adoc` once private submodules are available (owner: codex)

## Steps

1. Establish baseline per repo instructions.
2. Plan migration tasks and update docs references.
3. Run full QC suite before commits.

## Deliverables
- Updated docs across repos.
- Updated nav entries and playbook.
- Passing CI workflows.

## Quality Gates
- tests: pass
- linters/formatters: clean
- type-checks: clean
- security scan: clean
- coverage: ≥ baseline
- build: success
- docs updated

## Links
- PRs: TBD
- Files/lines: TBD

## Risks/Notes
- Pending baseline runs and repo-specific CI alignment.
- `osv-scanner` detected two outstanding `mcp` PyPI advisories and could not parse `requirements.workspace.txt`; follow-up task added for remediation.
