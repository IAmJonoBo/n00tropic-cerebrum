import { writeFileSync } from "node:fs";
import process from "node:process";

if (process.argv.length < 3) {
  console.error("Usage: node scripts/overwrite-file.mjs <path>");
  process.exit(2);
}
const file = process.argv[2];
const content = `# Vale local development guide

This repository uses Vale for documentation linting. CI uses Google and Microsoft styles; to keep local runs
faster and less noisy we provide a small local style \`n00\` that focuses on the checks that matter for day-to-day
work and allows fast iteration.

Quick commands

- vale sync — Refresh installed style packs and ensure local vocabulary is loaded
- VALE_LOCAL=1 make validate-docs — Run the lightweight \`n00\` checks (recommended while authoring)
- vale --output=JSON --ignore-syntax docs > artifacts/vale-full.json — Run a full CI-like check and write JSON to
  artifacts/vale-full.json

Developer helpers

- pnpm -s docs:vale-triage — Parse the full run JSON and create a triage report grouped by file and check. The
  triage report is written to artifacts/vale-triage.json.
- pnpm -s docs:fix-style — Apply a small set of safe editorial normalizations to \`.adoc\` files (commas, spacing,
  ellipses and other low-risk normalizations).
- pnpm -s docs:generate-spelling-counts — Produce a JSON with Vale.Spelling token counts to guide whitelist
  decisions.
- pnpm -s docs:vale-whitelist-candidates — Produce a shortlist of high-frequency tokens for review (candidates
  for whitelisting).

Notes

- Add project acronyms and tooling names into styles/config/vocabularies/n00/accept.txt and run vale sync.
- Use the triage report to prioritise fixes and to identify tokens worth whitelisting.

Markdown / AsciiDoc linting

- The repository contains a config.markdownlint-cli2.jsonc file tuned for AsciiDoc. It relaxes rules for long
  table lines, inline HTML, bare URLs, and other AsciiDoc-specific cases.
- To lint AsciiDoc files with the repository config, run:

  pnpm -s exec markdownlint-cli2 --config config.markdownlint-cli2.jsonc "docs/**/*.adoc"

Best practices

- Prefer using the \`n00\` local run while writing. Run the full CI-style Vale check (Google/Microsoft styles) to
  confirm final issues before a PR.
- Curate whitelists intentionally. Prefer whitelisting true project names / acronyms (e.g., \`ERPNext\`, \`Algolia\`,
  \`pnpm\`) rather than whitelisting typos.
- If you want to preview the editorial patches applied by docs:fix-style, run:

  node scripts/fix-docs-style.mjs --pattern "docs/**/*.adoc" --dry-run

If you'd like help, I can prepare a short PR that (1) curates a whitelist, (2) applies small editorial fixes across
 a subset of pages, and (3) re-runs the full Vale check to show the impact.
`;

writeFileSync(file, content, "utf8");
console.log("Wrote", file);
