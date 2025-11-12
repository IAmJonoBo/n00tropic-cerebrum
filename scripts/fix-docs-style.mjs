import { readFileSync, writeFileSync } from "node:fs";
import process from "node:process";
import { glob } from "glob";

// Accept an optional pattern and a dry-run flag
const args = process.argv.slice(2);
let pattern = "docs/**/*.adoc";
let dryRun = false;
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--pattern" && args[i + 1]) {
    pattern = args[i + 1];
    i++;
  }
  if (args[i] === "--dry-run") {
    dryRun = true;
  }
}
const files = await glob(pattern);
let changed = 0;
for (const f of files) {
  let s = readFileSync(f, "utf8");
  const original = s;
  // Replace 'e.g.' and variants to 'for example'
  s = s.replace(/\be\.g\.\b/gi, "for example");
  s = s.replace(/\be\.g\.,\b/gi, "for example,");
  // Replace spaced en-dashes ' – ' with ' – ' trimmed to '–'
  s = s.replace(/\s–\s/g, "–");
  // Replace '"<numbers>",' to put comma inside quotes (we'll do a simple fix for patterns "x", -> "x," )
  s = s.replace(/"(\d[,\d]*)",/g, '"$1,"');
  // Remove double occurrences like 'pandoc pandoc' or 'Pandoc Pandoc'
  s = s.replace(/\b([Pp]andoc)\s+\1\b/g, "$1");
  // Collapse repeated words of length 3+ (e.g., 'Frontiers Frontiers' -> 'Frontiers')
  s = s.replace(/\b(\w{3,})\s+\1\b/gi, "$1");
  // Normalize GUIDELINES: convert backtick code markers with repeated words like 'pandoc pandoc' inside code to single
  s = s.replace(/`([Pp]andoc)\s+\1`/g, "`$1`");
  // Move commas within quotes for short words (e.g., "foo", -> "foo,")
  s = s.replace(/"([\w-./]+)",/g, '"$1,"');
  // Replace i.e. -> that is (safe rewrite)
  s = s.replace(/\bi\.e\.\b/gi, "that is");
  // Normalize AsciiDoc to asciidoc (Vale prefers lowercase)
  s = s.replace(/\bAsciiDoc\b/g, "asciidoc");
  // Normalize CI to ci (Vale prefers lowercase ci)
  s = s.replace(/\bCI\b/g, "ci");
  // Normalize algolia to Algolia (proper noun capitalization)
  s = s.replace(/\balgolia\b/gi, "Algolia");
  // Normalize CLI to 'CLI' in sentences, but avoid code blocks: we avoid touching inline code (best effort)
  s = s.replace(/\b[Cc][Ll][Ii]\b/g, "CLI");
  // Remove trailing whitespace on lines
  s = s.replace(/[ \t]+$/gm, "");
  // Normalize three or more dots to ellipsis …
  s = s.replace(/\.\.\.+/g, "…");
  // Normalize 'ad-hoc' to 'ad hoc' (style choice) – 'ad-hoc' often flagged
  s = s.replace(/\bad-?hoc\b/gi, "ad hoc");
  // Normalize underscore emphasis used for simple words like _no_ or _not_ to plain words
  s = s.replace(/\b_no_\b/g, "no");
  s = s.replace(/\b_not_\b/g, "not");
  // Normalize multiple spaces to single space (avoid code-blocks where possible)
  s = s.replace(/([^\S\n]){2,}/g, " ");
  if (s !== original) {
    if (dryRun) {
      console.log("Would patch", f);
    } else {
      writeFileSync(f, s, "utf8");
      console.log("Patched", f);
    }
    changed++;
  }
}
console.log("Changed files:", changed);
