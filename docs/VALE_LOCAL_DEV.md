# Vale local development guide

This repository uses Vale for doc linting. CI uses Google & Microsoft styles; the `n00` style keeps local runs lightweight.

Commands

- Sync styles: `vale sync`
- Local dev run: `VALE_LOCAL=1 make validate-docs`
- Full run (CI-like): `vale --output=JSON --ignore-syntax docs > artifacts/vale-full.json`
- Generate triage: `pnpm -s docs:vale-triage`
- Apply safe fixes: `pnpm -s docs:fix-style`
- Generate spell counts: `pnpm -s docs:generate-spelling-counts`
- Suggest whitelists: `pnpm -s docs:vale-whitelist-candidates`

Notes

- Add vocabulary entries to `styles/config/vocabularies/n00/accept.txt` and run `vale sync` to make them effective in full runs.
- The triage script parse Vale's JSON even if Vale exits non-zero and writes `artifacts/vale-triage.json`.

# Vale local development guide

This repository uses Vale for documentation linting. The CI uses Google and Microsoft style packs, but a small local style `n00` reduces noise for local work.

Quick commands

- vale sync — Refresh installed style packs and ensure Verd or other packages are present
- VALE_LOCAL=1 make validate-docs — Run the local n00 style to check docs locally
- vale --output=JSON --ignore-syntax docs > artifacts/vale-full.json — Run CI-like full Vale check and write JSON results

Developer helpers

- pnpm -s docs:vale-triage — Parse the latest JSON and create a triage report grouped by file/check
- pnpm -s docs:fix-style — Apply a set of safe, low-risk editorial normalizations to docs
- pnpm -s docs:generate-spelling-counts — Produce a JSON with Vale.Spelling token counts
- pnpm -s docs:vale-whitelist-candidates — Produce a text file of candidate whitelist tokens for review

Notes

- Add project acronyms and tooling names into `styles/config/vocabularies/n00/accept.txt`. Then run `vale sync` and the full Vale run to verify the change reduces noise.
- The triage script handles Vale's non-zero exit codes and still parses the JSON output, which is saved to `artifacts/vale-triage.json`.

Next steps

- We can curate the high-frequency tokens and add them to the `n00` vocabulary or tweak copy to resolve true spelling issues. If you want, I can create a PR with a curated whitelist and a small set of safe fixes.

# Vale local development guide

This repository uses Vale for documentation linting. The CI uses Google and Microsoft style packs, but there is a small, conservative local style `n00` that keeps local runs developer-friendly.

How to run locally

- Sync official styles and refresh local vocabulary:
  - vale sync
- Run the local dev checks using the lightweight `n00` style:
  - VALE_LOCAL=1 make validate-docs
- Run a full CI-like Vale run (downloads Google/Microsoft styles):
  - vale --output=JSON --ignore-syntax docs > artifacts/vale-full.json

Helpful developer scripts

- Run the triage report (parses artifacts/vale-full.json and summarises check totals per file):
  - pnpm -s docs:vale-triage
- Apply a set of safe editorial normalizations (commas, spacing, ellipses, etc.) across docs:
  - pnpm -s docs:fix-style
- Generate a JSON of Vale.Spelling token counts and a shortlist of suggested whitelist tokens for manual review:
  - pnpm -s docs:generate-spelling-counts
  - pnpm -s docs:vale-whitelist-candidates

Notes

- The `n00` vocabulary is at `styles/config/vocabularies/n00/accept.txt`. It uses the Vale 'Vocab' system; add project-specific acronyms and tooling names here to reduce Vale.Spelling noise.
- We intentionally keep the CI checks (Google, Microsoft) as the authoritative gate; use the triage script to prioritise fixes and decide which tokens to whitelist or edit editorially.
- The triage script now handles Vale's non-zero exit code and will still parse the JSON output to produce a report.

If you'd like, I can open a PR that: (1) curates a small set of high-frequency tokens to whitelist, (2) adds a selected set of editorial fixes (safe, non-controversial edits), and (3) re-runs Vale to confirm the impact.

# Vale local development guide

This project uses Vale for documentation linting. Core style packs (Google and Microsoft) are used in CI, but a lightweight local "n00" style is available for developers to run Vale safely during local edits and triage.

Quick commands:

- Sync official styles and refresh local vocabulary:
  - vale sync
- Run a local (developer-friendly) Vale run with the `n00` style:
  - VALE_LOCAL=1 make validate-docs
- Run a full/CI Vale run (official Google / Microsoft rules):
  - vale --output=JSON --ignore-syntax docs > artifacts/vale-full.json
- Generate a triage report (full run):
  - pnpm -s docs:vale-triage
- Automatically apply a set of safe editorial style fixes:
  - pnpm -s docs:fix-style
- Generate spelling token counts and suggested whitelist candidates for review:
  - pnpm -s docs:generate-spelling-counts
  - pnpm -s docs:vale-whitelist-candidates

Notes:

- The `n00` vocabulary is located at `styles/config/vocabularies/n00/accept.txt`. Add project-specific acronyms or tooling names there to reduce irrelevant Vale.Spelling flags during full runs.
- The triage script now parses Vale's JSON output even when Vale exits with a non-zero code (finds issues). The triage report can be found at `artifacts/vale-triage.json`.
- If you add new tokens to the vocabulary, run `vale sync` and re-run tests for changes to apply.

If you'd like help adding a curated spelling whitelist or applying editorial corrections, run `pnpm -s docs:generate-spelling-counts` and then `pnpm -s docs:vale-whitelist-candidates` to produce a ready-to-review list.

- Run a full/CI Vale run (official Google / Microsoft rules):
- vale --output=JSON --ignore-syntax docs > artifacts/vale-full.json
- Generate a triage report (full run):
- pnpm -s docs:vale-triage
- Automatically apply a set of safe editorial style fixes:
- pnpm -s docs:fix-style
- Generate spelling token counts and suggested whitelist candidates for review:
- pnpm -s docs:generate-spelling-counts
- pnpm -s docs:vale-whitelist-candidates

Notes:

- The `n00` vocabulary is located at `styles/config/vocabularies/n00/accept.txt`. Add project-specific acronyms or tooling names there to reduce irrelevant Vale.Spelling flags during full runs.
- The triage script now parses Vale's JSON output even when Vale exits with a non-zero code (finds issues). The triage report can be found at `artifacts/vale-triage.json`.
- If you add new tokens to the vocabulary, run `vale sync` and re-run tests for changes to apply.

If you'd like help adding a curated spelling whitelist or applying editorial corrections, run `pnpm -s docs:generate-spelling-counts` and then `pnpm -s docs:vale-whitelist-candidates` to produce a ready-to-review list.

# Vale local development guide

This project uses Vale for documentation linting. Core style packs (Google and Microsoft) are used in CI, but a lightweight local "n00" style is available for developers to run Vale safely during local edits and triage.

Quick commands:

- Sync official styles and refresh local vocabulary:
  - vale sync
- Run a local (developer-friendly) Vale run with the `n00` style:
  - VALE_LOCAL=1 make validate-docs
- Run a full/CI Vale run (official Google / Microsoft rules):
  - vale --output=JSON --ignore-syntax docs > artifacts/vale-full.json
- Generate a triage report (full run):
  - pnpm -s docs:vale-triage
- Automatically apply a set of safe editorial style fixes:
  - pnpm -s docs:fix-style
- Generate spelling token counts and suggested whitelist candidates for review:
  - pnpm -s docs:generate-spelling-counts
  - pnpm -s docs:vale-whitelist-candidates

Notes:

- The `n00` vocabulary is located at `styles/config/vocabularies/n00/accept.txt`. Add project-specific acronyms or tooling names there to reduce irrelevant Vale.Spelling flags during full runs.
- The triage script now parses Vale's JSON output even when Vale exits with a non-zero code (finds issues). The triage report can be found at `artifacts/vale-triage.json`.
- If you add new tokens to the vocabulary, run `vale sync` and re-run tests for changes to apply.

If you'd like help adding a curated spelling whitelist or applying editorial corrections, run `pnpm -s docs:generate-spelling-counts` and then `pnpm -s docs:vale-whitelist-candidates` to produce a ready-to-review list.
