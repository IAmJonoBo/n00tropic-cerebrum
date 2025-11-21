#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const cwd = process.cwd();
const args = process.argv.slice(2);
const excludePatterns = [];

for (let i = 0; i < args.length; i += 1) {
  const arg = args[i];
  if (arg === "--exclude" || arg === "-x") {
    const value = args[i + 1];
    if (!value) {
      console.error("Missing value for --exclude");
      process.exit(2);
    }
    value.split(",").forEach((pattern) => {
      if (pattern.trim()) excludePatterns.push(pattern.trim());
    });
    i += 1;
  } else if (arg.startsWith("--exclude=")) {
    arg
      .slice("--exclude=".length)
      .split(",")
      .forEach((pattern) => {
        if (pattern.trim()) excludePatterns.push(pattern.trim());
      });
  }
}

const npmCommandPattern =
  "\\bnpm\\s+(?:run|start|test|install|ci|audit|exec|publish|add|remove|update|upgrade|link|config|set|init|login|logout|whoami|cache|prune|outdated|dedupe|list|ls|pack|rebuild|root|search|version)(?:\\s|$|--)";

const rgArgs = [
  "--with-filename",
  "--line-number",
  "--no-heading",
  "--regexp",
  npmCommandPattern,
  ".",
];

for (const pattern of excludePatterns) {
  // If the pattern is a file (e.g. scripts/setup-pnpm.sh) or explicitly
  // contains a glob or extension, leave it as-is. Otherwise, treat it as a
  // directory and append '/**' to exclude all files under it.
  let normalized;
  if (pattern.endsWith("/**")) {
    normalized = pattern;
  } else if (pattern.endsWith("/")) {
    normalized = `${pattern}**`;
  } else if (path.extname(pattern) || pattern.includes("*")) {
    normalized = pattern; // file or explicit glob
  } else {
    normalized = `${pattern.replace(/\/$/, "")}/**`;
  }
  rgArgs.push("--glob");
  rgArgs.push(`!${normalized}`);
}

const rg = spawnSync("rg", rgArgs, { cwd, encoding: "utf8" });

if (rg.error) {
  console.error("Failed to execute ripgrep (rg):", rg.error.message);
  process.exit(2);
}

if (rg.status === 2) {
  console.error(rg.stderr || "ripgrep reported an error.");
  process.exit(2);
}

const lines = rg.stdout ? rg.stdout.trim().split("\n").filter(Boolean) : [];

if (!lines.length) {
  process.exit(0);
}

console.error("Found npm references:");
for (const line of lines) {
  const first = line.indexOf(":");
  const second = line.indexOf(":", first + 1);
  if (first === -1 || second === -1) {
    console.error(line);
    continue;
  }
  const file = line.slice(0, first);
  const lineNumber = line.slice(first + 1, second);
  const text = line.slice(second + 1).trim();
  const rel = path.relative(cwd, file);
  console.error(`- ${rel}:${lineNumber} -> ${text}`);
}
process.exit(1);
