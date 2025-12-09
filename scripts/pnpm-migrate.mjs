#!/usr/bin/env node
/**
 * pnpm-migrate.mjs
 *
 * Orchestrates the existing npm→pnpm migration helpers so you don’t have to remember three scripts.
 *
 * Usage:
 *   pnpm-migrate find [--exclude=pattern1,pattern2]
 *   pnpm-migrate replace-npx [--apply|--dry-run] [--dirs=dir1,dir2] [--exclude=dirA,dirB]
 *   pnpm-migrate replace-npm [--apply|--dry-run] --dirs=dir1,dir2 [--exclude=dirA,dirB] [--no-backup]
 *   pnpm-migrate all --dirs=dir1,dir2 [--exclude=dirA,dirB] [--apply]  # runs replace-npm, replace-npx, then find
 */

import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");

const subcommand = process.argv[2];
const passthrough = process.argv.slice(3);

const scripts = {
  find: path.join(root, "scripts", "find-npm-usages.mjs"),
  replaceNpx: path.join(root, "scripts", "replace-npx-with-pnpm.mjs"),
  replaceNpm: path.join(root, "scripts", "replace-npm-commands-with-pnpm.mjs"),
};

function runNode(script, args = []) {
  const result = spawnSync("node", [script, ...args], {
    cwd: root,
    stdio: "inherit",
    env: process.env,
  });
  if (result.error) {
    console.error(`Failed to run ${path.basename(script)}:`, result.error);
    process.exit(result.status ?? 1);
  }
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function printHelp() {
  console.log(`pnpm-migrate

Usage:
  pnpm-migrate find [--exclude=pattern1,pattern2]
  pnpm-migrate replace-npx [--apply|--dry-run] [--dirs=dir1,dir2] [--exclude=dirA,dirB]
  pnpm-migrate replace-npm [--apply|--dry-run] --dirs=dir1,dir2 [--exclude=dirA,dirB] [--no-backup]
  pnpm-migrate all --dirs=dir1,dir2 [--exclude=dirA,dirB] [--apply]

Notes:
  - 'all' runs replace-npm (docs/examples), then replace-npx, then a final 'find' to surface stragglers.
  - Provide --apply to actually write changes; omit to dry-run where supported.
  - --exclude patterns are forwarded to the underlying scripts.
`);
}

switch (subcommand) {
  case "find":
    runNode(scripts.find, passthrough);
    break;
  case "replace-npx":
    runNode(scripts.replaceNpx, passthrough);
    break;
  case "replace-npm":
    runNode(scripts.replaceNpm, passthrough);
    break;
  case "all": {
    // Ensure we default to dry-run unless user explicitly set --apply
    const hasApply = passthrough.includes("--apply");
    const applyArgs = hasApply ? passthrough : [...passthrough, "--dry-run"];
    runNode(scripts.replaceNpm, applyArgs);
    runNode(scripts.replaceNpx, applyArgs);
    runNode(scripts.find, []);
    break;
  }
  default:
    printHelp();
    process.exit(subcommand ? 1 : 0);
}
