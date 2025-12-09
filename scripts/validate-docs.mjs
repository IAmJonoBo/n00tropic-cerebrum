#!/usr/bin/env node
/**
 * Lightweight replacement for `make validate-docs` so agents can run
 * `pnpm run validate-docs` without assuming GNU Make.
 */

import { spawnSync } from "node:child_process";
import process from "node:process";

const isWindows = process.platform === "win32";

function commandExists(binary) {
  const checker = isWindows ? "where" : "which";
  const result = spawnSync(checker, [binary], { stdio: "ignore" });
  return result.status === 0;
}

function runCommand(cmd, args, options = {}) {
  const res = spawnSync(cmd, args, { stdio: "inherit", ...options });
  if (res.error) {
    throw res.error;
  }
  return typeof res.status === "number" ? res.status : 1;
}

function logHeader(message) {
  console.log("\n==> %s", message);
}

let exitCode = 0;

const skipVale = process.env.SKIP_VALE === "1";
if (skipVale) {
  console.log("SKIP_VALE set: skipping Vale checks.");
} else if (!commandExists("vale")) {
  console.log("Vale not installed; skipping Vale checks.");
} else {
  logHeader("Running Vale");
  const valeArgs = [];
  if (process.env.VALE_LOCAL === "1") {
    console.log("Using .vale.local.ini with syntax ignore mode.");
    valeArgs.push("--config", ".vale.local.ini", "--ignore-syntax");
  }
  // Temporarily exclude agent-facing policy pages from Vale while we iterate on tone
  valeArgs.push("docs/**/*.adoc");
  exitCode = runCommand("vale", valeArgs);
}

if (exitCode === 0) {
  if (!commandExists("lychee")) {
    console.log("Lychee not installed; skipping link checks.");
  } else {
    logHeader("Running Lychee");
    exitCode = runCommand("lychee", [
      "--config",
      ".lychee.toml",
      "docs/**/*.adoc",
    ]);
  }
}

if (exitCode === 0) {
  logHeader("Checking Antora attributes");
  exitCode = runCommand(process.execPath, ["scripts/check-attrs.mjs"]);
}

process.exit(exitCode);
