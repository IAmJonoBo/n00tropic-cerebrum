# Automation Script Index

Canonical entrypoints (also available via `bin/workspace`):

- `workspace-health.sh` — health snapshot, submodule sync, clean-untracked (optional), artifact publish
- `meta-check.sh` — cross-repo lint/test/ingest orchestration
- `workspace-release.sh` — release dry-run/manifest emit
- `deps-audit.sh` — osv-scanner + pip-audit wrappers
- `ingest-frontiers.sh` — frontiers export ingestion helper
- `refresh-workspace.sh` — fetch/sync helpers

Category helpers:

- **Docs**: `docs-build.sh`, `docs-lint.sh`, `docs-sync-super.sh`, `docs-verify.sh`
- **Deps**: `deps-drift.py`, `deps-renovate-dry-run.sh`, `deps-sbom.sh`, `deps-dependency-track-upload.sh`
- **Project metadata**: `validate-project-metadata.py`, `autofix-project-metadata.py`, `project-autofix-links.sh`
- **Quality**: `trunk-lint-run.sh`, `run-trunk-subrepos.sh`, `workspace-health.py`
- **Release/logging**: `workspace-health.sh --publish-artifact`, `record-run-envelope.py`, `record-capability-run.py`

Notes:

- Prefer `bin/workspace <cmd>` for day-to-day ops; this README is a quick map for agents and humans.
- Legacy/rare scripts remain for backwards compatibility; consider migrating to the canonical entrypoints above before deprecating.
