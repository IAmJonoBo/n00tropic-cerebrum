# Golden Path: Workspace

- `source scripts/ensure-nvm-node.sh` (auto nvm use/install from .nvmrc).
- `scripts/bootstrap-workspace.sh` (submodules, skeleton, hooks, nvmrc sync, python bootstrap).
- `pnpm -C n00plicate tokens:orchestrate && pnpm -C n00plicate tokens:validate` (placeholder Penpot export; replace with real export at release).
- `.dev/automation/scripts/policy-sync.sh --check` (frontiers ingest → cortex validate → n00menon sync → releases snapshot).
- `scripts/workspace-graph-export.sh` (emits workspace graph + capability health).
- Optional guards: `workspace.toolchainPins`, `workspace.tokensDrift`, `search.typesenseFreshness`.

Per-repo golden paths live in each repo’s `GOLDEN_PATH.md` and are mirrored in `docs/modules/ROOT/pages/golden-paths.adoc` and `n00menon/modules/ROOT/pages/golden-paths.adoc`.
