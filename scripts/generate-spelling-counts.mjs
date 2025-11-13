import fs from "node:fs";

const p = "artifacts/vale-full.json";
if (!fs.existsSync(p)) {
  console.error("No", p);
  process.exit(1);
}
const data = JSON.parse(fs.readFileSync(p, "utf8"));
const map = {};
for (const f in data) {
  for (const issue of data[f]) {
    if (issue.Check === "Vale.Spelling") {
      const match = issue.Match || issue.Message || "";
      if (!match) continue;
      const key = String(match).trim();
      map[key] = (map[key] || 0) + 1;
    }
  }
}
const arr = Object.entries(map).sort((a, b) => b[1] - a[1]);
const out = arr.map(([k, v]) => ({ term: k, count: v }));
fs.writeFileSync(
  "artifacts/vale-spelling-token-counts.json",
  JSON.stringify(out, null, 2),
);
console.log(
  "Wrote artifacts/vale-spelling-token-counts.json with",
  out.length,
  "entries",
);
