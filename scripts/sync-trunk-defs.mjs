#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(new URL(import.meta.url)));
const root = path.resolve(here, "..");
const helper = path.join(
  root,
  ".dev",
  "automation",
  "scripts",
  "sync-trunk-configs.sh",
);

if (!fs.existsSync(helper)) {
  console.error(`[sync-trunk-defs] Missing helper: ${helper}`);
  process.exit(2);
}

const modeFlags = new Set(["--pull", "--write", "--check", "--push"]);
const forwarded = process.argv.slice(2);
const hasModeFlag = forwarded.some((arg) => modeFlags.has(arg));
const args =
  forwarded.length === 0 || !hasModeFlag ? ["--pull", ...forwarded] : forwarded;

const result = spawnSync(helper, args, {
  cwd: root,
  stdio: "inherit",
  env: { ...process.env },
});

if (result.error) {
  console.error(
    `[sync-trunk-defs] Failed to launch sync helper: ${result.error.message}`,
  );
  process.exit(2);
}

process.exit(result.status ?? 1);
