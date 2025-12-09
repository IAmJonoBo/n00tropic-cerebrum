#!/usr/bin/env node
import fs from "node:fs";

const LEVELS = ["debug", "info", "warn", "error", "fatal"];

function log(level, message, meta = {}) {
  const lvl = LEVELS.includes(level) ? level : "info";
  const entry = {
    ts: new Date().toISOString(),
    level: lvl,
    message,
    ...meta,
  };
  const line = JSON.stringify(entry);
  if (process.env.HUMAN_LOG === "1") {
    const metaKeys = Object.keys(meta).filter(
      (k) => k !== "ts" && k !== "level",
    );
    const suffix = metaKeys.length
      ? ` | ${metaKeys.map((k) => `${k}=${meta[k]}`).join(" ")}`
      : "";
    console.log(`[${entry.ts}] ${lvl.toUpperCase()}: ${message}${suffix}`);
  } else {
    console.log(line);
  }
  const metricPath = process.env.METRIC_LOG;
  if (metricPath) {
    try {
      fs.appendFileSync(metricPath, line + "\n", "utf8");
    } catch (err) {
      // logging failures are non-fatal
    }
  }
}

export default { log };
export { log };
