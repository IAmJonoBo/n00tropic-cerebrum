import fs from "fs";

const p = "artifacts/vale-spelling-token-counts.json";
if (!fs.existsSync(p)) {
  console.error("No", p, "- run generate-spelling-counts.mjs first.");
  process.exit(1);
}
const counts = JSON.parse(fs.readFileSync(p, "utf8"));
// Read existing vocab
const existing = new Set();
if (fs.existsSync("styles/n00/vocab.txt")) {
  const txt = fs.readFileSync("styles/n00/vocab.txt", "utf8");
  txt.split(/\r?\n/).forEach((l) => {
    if (l.trim()) existing.add(l.trim());
  });
}
// Read Terms.yml tokens
if (fs.existsSync("styles/n00/Terms.yml")) {
  const txt = fs.readFileSync("styles/n00/Terms.yml", "utf8");
  const tokens = [...txt.matchAll(/"([^\"]+)"/g)].map((m) => m[1]);
  for (const t of tokens) existing.add(t);
}
// Read .vale.ini TokenIgnores
if (fs.existsSync(".vale.ini")) {
  const txt = fs.readFileSync(".vale.ini", "utf8");
  const m = txt.match(/TokenIgnores\s*=\s*(.*)/);
  if (m) {
    m[1]
      .split(",")
      .map((s) => s.trim())
      .forEach((t) => {
        if (t) existing.add(t);
      });
  }
}

// Threshold: show tokens with count >= 3
const threshold = 3;
const candidates = counts.filter(
  (c) => c.count >= threshold && !existing.has(c.term),
);
if (candidates.length === 0) {
  console.log(
    "No new high-frequency tokens need whitelisting (threshold",
    threshold,
    ").",
  );
  process.exit(0);
}
const out = candidates.map((c) => `${c.term}  # ${c.count}`);
fs.writeFileSync(
  "artifacts/vale-whitelist-suggestions.txt",
  out.join("\n") + "\n",
);
console.log(
  "Wrote artifacts/vale-whitelist-suggestions.txt with",
  out.length,
  "entries (threshold",
  threshold,
  ").",
);
