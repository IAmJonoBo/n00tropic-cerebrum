import { readFileSync, writeFileSync } from "node:fs";
import process from "node:process";

if (process.argv.length < 3) {
  console.error("Usage: node scripts/dedupe-file.mjs <path>");
  process.exit(2);
}
const file = process.argv[2];
const s = readFileSync(file, "utf8");
const header = "# Vale local development guide";
const first = s.indexOf(header);
if (first === -1) {
  console.error("Header not found in file. Nothing to do.");
  process.exit(1);
}
const second = s.indexOf(header, first + 1);
if (second === -1) {
  console.log("No duplicate header instances found; nothing to do.");
  process.exit(0);
}
const cleaned = s.substring(0, second);
writeFileSync(file, cleaned, "utf8");
console.log(
  "Cleaned duplicate content in",
  file,
  "by keeping the first section.",
);
