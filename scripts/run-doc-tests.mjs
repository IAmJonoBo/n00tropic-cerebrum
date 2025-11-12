#!/usr/bin/env node
import { glob } from "glob";
import { spawnSync } from "child_process";
import path from "node:path";
import { existsSync } from "node:fs";
const patterns = [
  "n00-frontiers/tests/**/*.js",
  "n00-frontiers/tests/**/*.ts",
  "n00-frontiers/tests/**/*.tsx",
  "n00-cortex/tests/**/*.js",
  "n00-cortex/tests/**/*.ts",
  "n00-cortex/tests/**/*.tsx",
  "n00t/tests/**/*.js",
  "n00t/tests/**/*.ts",
  "n00t/tests/**/*.tsx",
];
let found = false;
for (const p of patterns) {
  const files = await glob(p, { dot: false });
  if (files.length) {
    console.log(`Detected test files for pattern ${p}:`);
    files.forEach((f) => {
      console.log(` - ${f}`);
    });
    found = true;
    break;
  }
}
if (!found) {
  console.log("No JS/TS tests found for docs-only; skipping vitest run.");
  process.exit(0);
}
let res = { status: 0 };
for (const repo of ["n00-frontiers", "n00-cortex", "n00t"]) {
  const p = `${repo}/tests`;
  const js = await glob(`${p}/**/*.js`);
  const ts = await glob(`${p}/**/*.ts`);
  const tsx = await glob(`${p}/**/*.tsx`);
  if (js.length || ts.length || tsx.length) {
    console.log(`Running vitest in ${repo}`);
    // run vitest from the package root so that package-level config is used
    const repoPath = path.resolve(process.cwd(), repo);
    const localConfig = path.join(repoPath, "vitest.config.ts");
    // Build an explicit list of test files to run to avoid relying on config 'include' filters.
    const filesToRun = [];
    const docTestRegex = /(check-attrs|docs|antora|convert|sync-workflows)/i;
    js.forEach((f) => {
      if (docTestRegex.test(f))
        filesToRun.push(
          path.relative(repoPath, path.resolve(process.cwd(), f)),
        );
    });
    ts.forEach((f) => {
      if (docTestRegex.test(f))
        filesToRun.push(
          path.relative(repoPath, path.resolve(process.cwd(), f)),
        );
    });
    tsx.forEach((f) => {
      if (docTestRegex.test(f))
        filesToRun.push(
          path.relative(repoPath, path.resolve(process.cwd(), f)),
        );
    });
    // console.log(`Will run vitest with explicit files for ${repo}: ${filesToRun.join(', ')}`);
    if (filesToRun.length === 0) {
      console.log(`No doc-related test files to run for ${repo}`);
      continue;
    }
    if (existsSync(localConfig)) {
      // Run with package-local vitest config and explicit files
      res = spawnSync(
        "pnpm",
        ["exec", "--", "vitest", "run", ...filesToRun, "--reporter", "verbose"],
        { stdio: "inherit", cwd: repoPath },
      );
    } else {
      // Run with workspace root config but explicit file args so we only run per-repo tests
      res = spawnSync(
        "pnpm",
        [
          "exec",
          "--",
          "vitest",
          "run",
          ...filesToRun,
          "--reporter",
          "verbose",
          "--config",
          path.resolve(process.cwd(), "vitest.config.ts"),
        ],
        { stdio: "inherit", cwd: repoPath },
      );
    }
    if (res.status !== 0) break;
  }
}
process.exit(res.status ?? 1);
