import { readFileSync } from "node:fs";
import { glob } from "glob";

const files = await glob("docs/modules/**/pages/**/*.adoc");
let failed = false, now = new Date();

for (const f of files) {
  const s = readFileSync(f, "utf8");
  const hasTags = /^:page-tags:\s?.+/m.test(s);
  const m = /^:reviewed:\s?(\d{4}-\d{2}-\d{2})/m.exec(s);
  if (!hasTags) { console.error(`Missing :page-tags: -> ${f}`); failed = true; }
  if (!m) { console.error(`Missing :reviewed: -> ${f}`); failed = true; }
  else {
    const dt = new Date(m[1]);
    const age = (now - dt) / (1000*60*60*24);
    if (age > 90) { console.error(`Stale :reviewed: (${m[1]}) -> ${f}`); failed = true; }
  }
}
if (failed) process.exit(1);
