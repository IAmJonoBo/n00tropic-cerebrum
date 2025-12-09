#!/usr/bin/env node
// Guard to ensure pnpm install is run from the current repo root (subrepo) and not from the workspace root.
// Intended to be wired as a preinstall script inside subrepo package.json files.
// Allows override with ALLOW_SUBREPO_PNPM_INSTALL=1 (or CI).
import fs from "node:fs";
import path from "node:path";

const allow =
  process.env.ALLOW_SUBREPO_PNPM_INSTALL === "1" || process.env.CI === "1";
const cwd = process.cwd();
const pkgPath = path.join(cwd, "package.json");
if (!fs.existsSync(pkgPath)) {
  console.error(
    "[guard-subrepo-pnpm-install] package.json not found in CWD; run pnpm install from repo root.",
  );
  if (!allow) process.exit(1);
}
// extra sanity: ensure not accidentally at workspace root
const rootNvmrc = path.join(cwd, "../.nvmrc");
const workspacePkg = path.join(cwd, "../package.json");
if (fs.existsSync(rootNvmrc) && fs.existsSync(workspacePkg) && !allow) {
  const rootPkg = JSON.parse(fs.readFileSync(workspacePkg, "utf8"));
  if (rootPkg.name === "n00tropic-cerebrum") {
    console.error(
      "[guard-subrepo-pnpm-install] Detected workspace root nearby; run pnpm --filter <subrepo> install from the workspace or install inside the subrepo after cd.",
    );
    process.exit(1);
  }
}
