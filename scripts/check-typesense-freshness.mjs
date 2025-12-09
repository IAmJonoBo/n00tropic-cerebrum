#!/usr/bin/env node
/**
 * Fails if the latest Typesense reindex log is older than MAX_DAYS (default 7).
 * Looks for docs/search/logs/typesense-reindex-*.log or .log.json.
 */
import fs from "node:fs";
import path from "node:path";

const LOG_DIR = "docs/search/logs";
const MAX_DAYS = Number(process.env.TYPESENSE_MAX_AGE_DAYS || "7");
const WARN_DAYS = Number(process.env.TYPESENSE_WARN_AGE_DAYS || "5");

function findLatest() {
  if (!fs.existsSync(LOG_DIR)) return null;
  const entries = fs
    .readdirSync(LOG_DIR)
    .filter((f) => f.startsWith("typesense-reindex-"))
    .map((f) => path.join(LOG_DIR, f));
  if (entries.length === 0) return null;
  return entries
    .map((p) => ({ p, mtime: fs.statSync(p).mtime }))
    .sort((a, b) => b.mtime - a.mtime)[0].p;
}

function daysAgo(date) {
  return (Date.now() - date.getTime()) / (1000 * 60 * 60 * 24);
}

const latest = findLatest();
if (!latest) {
  console.error(
    "Typesense freshness check: no log found under docs/search/logs/",
  );
  process.exit(1);
}

let captured = fs.statSync(latest).mtime;

// If JSON summary exists, prefer its captured_at value
if (latest.endsWith(".log")) {
  const jsonPath = `${latest}.json`;
  if (fs.existsSync(jsonPath)) {
    try {
      const parsed = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
      if (parsed.captured_at) captured = new Date(parsed.captured_at);
    } catch (err) {
      // ignore parse errors, fallback to mtime
    }
  }
}

const age = daysAgo(captured);
if (age > MAX_DAYS) {
  console.error(
    `Typesense freshness check failed: ${path.basename(latest)} is ${age.toFixed(
      1,
    )} days old (max ${MAX_DAYS})`,
  );
  process.exit(1);
}

if (age > WARN_DAYS) {
  console.warn(
    `Typesense freshness warning: ${path.basename(latest)} is ${age.toFixed(
      1,
    )} days old (> warn ${WARN_DAYS}, <= max ${MAX_DAYS})`,
  );
} else {
  console.log(
    `Typesense freshness OK: ${path.basename(latest)} age=${age.toFixed(1)} days (<= ${MAX_DAYS})`,
  );
}
