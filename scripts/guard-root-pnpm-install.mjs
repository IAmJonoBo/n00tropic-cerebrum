#!/usr/bin/env node
// Prevent accidental `pnpm install` at the workspace root which can rewrite subrepo locks/hoists.
// Allow overrides via ALLOW_ROOT_PNPM_INSTALL=1 or CI=1.

import path from "node:path";

const cwd = process.cwd();
const root = path.resolve(path.join(import.meta.url.startsWith("file:") ? new URL(import.meta.url).pathname : __dirname, ".."));
const allow = process.env.ALLOW_ROOT_PNPM_INSTALL === "1" || process.env.CI === "1";

if (path.resolve(cwd) === path.resolve(root) && !allow) {
  console.error(
    "\n[guard-root-pnpm-install] Refusing to run pnpm install at workspace root to protect subrepo locks.\n" +
      "Set ALLOW_ROOT_PNPM_INSTALL=1 if you really intend to install here, or run inside a subrepo (pnpm --filter ... install).\n",
  );
  process.exit(1);
}
