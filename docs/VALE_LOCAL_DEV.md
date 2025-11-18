<!-- vale Vale.Spelling = NO -->

# Vale local development guide

This workspace uses Vale for documentation linting. CI uses Google and Microsoft styles; to keep local runs
faster and less noisy the docs team provides a small local style `n00` that focuses on the checks that matter for day-to-day
work and allows fast iteration.

Quick commands

- `vale sync` -- Refresh installed style packs and ensure local vocabulary is loaded
- `VALE_LOCAL=1 make validate-docs` -- Run the lightweight `n00` checks (recommended while authoring)
- `vale --output=JSON --ignore-syntax docs > artifacts/vale-full.json` -- Run a full CI-like check and write JSON to
  artifacts/vale-full.json

Developer helpers

- `pnpm -s docs:vale-triage` -- Parse the full run JSON and create a triage report grouped by file and check. The
  triage report is written to artifacts/vale-triage.json.
- `pnpm -s docs:fix-style` -- Apply a small set of safe editorial normalizations to `.adoc` files (commas, spacing,
  ellipses and other low-risk normalizations).
- `pnpm -s docs:generate-spelling-counts` -- Produce a JSON with `Vale.Spelling` token counts to guide whitelist
  decisions.
- `pnpm -s docs:vale-whitelist-candidates` -- Produce a shortlist of high-frequency tokens for review (candidates
  for whitelisting).
- `pnpm -s docs:vale-terms-candidates` -- Produce a shortlist of frequent `Vale.Terms` tokens and proposed edits or
  whitelist candidates. Flags: `--threshold <n>`, `--dry-run`, `--output <file>`, `--json <path>`
  Additional flags: `--whitelist [vocab|terms]` (append tokens to `styles/n00/vocab.txt` by default),
  `--apply-edits` (apply Vale-suggested editorial replacements conservatively), `--interactive` (prompt for
  confirmation), and `--yes` (skip confirmation prompts).

Tip: `vale-whitelist-candidates.mjs` accepts `--threshold <n>` to lower the frequency threshold for candidates; the
default is 3. For example:

node scripts/vale-whitelist-candidates.mjs --threshold 2

Notes

- Add project acronyms and tooling names into styles/config/vocabularies/n00/accept.txt and run `vale sync`.
- Use the triage report to prioritise fixes and to identify tokens worth whitelisting.

Notes about edits and backups

- `--apply-edits` creates a backup of any edited file at `{path}.bak` before writing changes.
- Prefer running `--apply-edits --dry-run` to preview edits. Then run `--apply-edits --yes` to apply.
- `--whitelist` appends tokens to `styles/n00/vocab.txt` by default. Use `--whitelist terms` to append to `styles/n00/Terms.yml` instead.

Markdown / AsciiDoc linting

- The workspace contains a `config.markdownlint-cli2.jsonc` file tuned for AsciiDoc. It relaxes rules for long
  table lines, inline HTML, bare URLs, and other AsciiDoc-specific cases.
- To lint asciidoc files with the repository config, run:

pnpm -s exec markdownlint-cli2 --config config.markdownlint-cli2.jsonc "docs/\*_/_.adoc"

Best practices

- Prefer using the `n00` local run while writing. Run the full CI-style Vale check (Google/Microsoft styles) to
  confirm final issues before a PR.
- Curate whitelists intentionally. Prefer whitelisting true project names / acronyms (for example, `ERPNext`, `Algolia`,
  `pnpm`) rather than whitelisting typos.
- If you want to preview the editorial patches applied by docs:fix-style, run:

node scripts/fix-docs-style.mjs --pattern "docs/\*_/_.adoc" --dry-run

Need an extra set of eyes? Open an issue describing the desired scope (for example, curate a whitelist, apply
editorial fixes across a subset of pages, and re-run the full Vale check) so the docs maintainers can assist.

CI and validation hooks

- The workspace includes a polyrepo health check that runs Python formatting and linting across the
  workspace. You can run it locally by invoking the pnpm script:

pnpm run lint:python

The automation CI runs this script automatically as part of the `workspace-health` workflow.

<!-- vale Vale.Spelling = YES -->
