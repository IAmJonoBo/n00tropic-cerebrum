#!/usr/bin/env node
/**
 * Summarize :page-tags: usage across docs. Helps spot inconsistent tagging.
 */
import { globSync } from "glob";
import fs from "node:fs";

const files = globSync("docs/modules/**/pages/**/*.adoc");
const counts = new Map();

for (const f of files) {
  const m = /^:page-tags:\s*(.+)$/m.exec(fs.readFileSync(f, "utf8"));
  if (!m) continue;
  const tags = m[1].split(",").map((t) => t.trim());
  for (const t of tags) {
    counts.set(t, (counts.get(t) || 0) + 1);
  }
}

const sorted = Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
for (const [tag, n] of sorted) {
  console.log(`${tag}: ${n}`);
}
