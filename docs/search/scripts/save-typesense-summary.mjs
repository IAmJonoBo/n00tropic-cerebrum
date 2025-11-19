#!/usr/bin/env node
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const [logArg, outputArg] = process.argv.slice(2);
if (!logArg) {
  console.error(
    "Usage: node docs/search/scripts/save-typesense-summary.mjs <log-file> [output.json]",
  );
  process.exit(1);
}

const logPath = resolve(logArg);
const outputPath = resolve(outputArg || `${logPath}.json`);

let content;
try {
  content = readFileSync(logPath, "utf8");
} catch (error) {
  console.error(`Unable to read ${logPath}:`, error.message);
  process.exit(1);
}

const summary = {
  log_path: logPath,
  captured_at: new Date().toISOString(),
};

const docMatch = content.match(/DocSearch:\s+(\S+)\s+(\d+)\s+records/i);
if (docMatch) {
  summary.url = docMatch[1];
  summary.records = Number.parseInt(docMatch[2], 10);
}

if (summary.records == null) {
  const hitsMatch = content.match(/Nb hits:\s+(\d+)/i);
  if (hitsMatch) {
    summary.records = Number.parseInt(hitsMatch[1], 10);
  }
}

writeFileSync(outputPath, `${JSON.stringify(summary, null, 2)}\n`, "utf8");
console.log(`Typesense scrape summary -> ${outputPath}`);
