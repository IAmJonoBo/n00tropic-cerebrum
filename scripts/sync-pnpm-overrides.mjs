#!/usr/bin/env node
// Keep pnpm overrides and toolchain pins aligned across node repos.
// Defaults to apply changes; use --check to fail if drift is detected.
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const args = process.argv.slice(2);
const checkOnly = args.includes("--check");

const manifestPath = path.join(
  root,
  "n00-cortex",
  "data",
  "toolchain-manifest.json",
);
const overridePath = path.join(
  root,
  "n00-cortex",
  "data",
  "dependency-overrides",
  "pnpm-overrides.json",
);
const workspaceManifestPath = path.join(
  root,
  "automation",
  "workspace.manifest.json",
);

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function loadTargets() {
  const targets = new Set(["."]); // workspace root
  if (fs.existsSync(workspaceManifestPath)) {
    const manifest = readJson(workspaceManifestPath);
    for (const repo of manifest.repos || []) {
      const eligible =
        repo.pkg === "pnpm" ||
        repo.language === "node" ||
        repo.language === "mixed";
      if (eligible && repo.path) targets.add(repo.path);
    }
  }
  return Array.from(targets);
}

const toolchain = readJson(manifestPath);
const overrides = readJson(overridePath).overrides || {};
const expectedPnpm = toolchain.toolchains?.pnpm?.version;
const expectedNode = toolchain.toolchains?.node?.version;

function ensureEngines(pkg) {
  pkg.engines = pkg.engines || {};
  if (expectedNode) pkg.engines.node = pkg.engines.node || `>=${expectedNode}`;
  if (expectedPnpm) pkg.engines.pnpm = pkg.engines.pnpm || `>=${expectedPnpm}`;
}

function ensurePackageManager(pkg) {
  if (expectedPnpm) {
    const desired = `pnpm@${expectedPnpm}`;
    if (pkg.packageManager !== desired) {
      pkg.packageManager = desired;
      return true;
    }
  }
  return false;
}

function mergeOverrides(pkg) {
  const pnpmSection = pkg.pnpm || {};
  const existing = { ...(pnpmSection.overrides || pkg.overrides || {}) };
  const resolved = {};
  for (const [name, val] of Object.entries(overrides)) {
    if (val && typeof val === "object" && "version" in val) {
      resolved[name] = val.version;
    } else {
      resolved[name] = val;
    }
  }
  const merged = { ...existing, ...resolved };
  pnpmSection.overrides = merged;
  pkg.pnpm = pnpmSection;
  return JSON.stringify(existing) !== JSON.stringify(merged);
}

function processPackage(pkgPath) {
  const pkg = readJson(pkgPath);
  let changed = false;
  changed = mergeOverrides(pkg) || changed;
  changed = ensurePackageManager(pkg) || changed;
  const enginesBefore = JSON.stringify(pkg.engines || {});
  ensureEngines(pkg);
  if (JSON.stringify(pkg.engines || {}) !== enginesBefore) changed = true;

  if (changed && !checkOnly) {
    fs.writeFileSync(pkgPath, `${JSON.stringify(pkg, null, 2)}\n`);
  }
  return changed;
}

function main() {
  if (!fs.existsSync(manifestPath)) {
    console.error("[pnpm-overrides] missing toolchain manifest", manifestPath);
    return 1;
  }
  if (!fs.existsSync(overridePath)) {
    console.error("[pnpm-overrides] missing overrides", overridePath);
    return 1;
  }

  const targets = loadTargets();
  const drifts = [];

  for (const rel of targets) {
    const pkgPath = path.join(root, rel, "package.json");
    if (!fs.existsSync(pkgPath)) continue;
    const changed = processPackage(pkgPath);
    if (changed) drifts.push(rel || ".");
  }

  if (drifts.length === 0) {
    console.log("[pnpm-overrides] all package.json files aligned.");
    return 0;
  }

  if (checkOnly) {
    console.error(
      `[pnpm-overrides] drift detected in: ${drifts.join(", ")} (re-run without --check to apply)`,
    );
    return 1;
  }

  console.log(
    `[pnpm-overrides] updated overrides/toolchain fields in: ${drifts.join(", ")}`,
  );
  return 0;
}

process.exit(main());
