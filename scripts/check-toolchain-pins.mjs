#!/usr/bin/env node
// Verify that Node (.nvmrc) and pnpm pins match the canonical toolchain manifest
// and that subrepos agree with the workspace versions. Also verifies Python pins
// via .python-version using overrides from n00-cortex/data/dependency-overrides/.
import fs from "node:fs";
import path from "node:path";
import { log } from "./lib/log.mjs";
import { notifyDiscord } from "./lib/notify-discord.mjs";

const root = process.cwd();
const manifestPath = path.join(
  root,
  "n00-cortex",
  "data",
  "toolchain-manifest.json",
);
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
const expectedNode = (manifest.toolchains?.node?.version || "").trim();
const expectedPnpm = (manifest.toolchains?.pnpm?.version || "").trim();
const expectedPython = (manifest.toolchains?.python?.version || "").trim();
const webhook = process.env.DISCORD_WEBHOOK;
const argv = process.argv.slice(2);
const asJson = argv.includes("--json");
const workspaceManifestPath = path.join(
  root,
  "automation",
  "workspace.manifest.json",
);
const overrideDir = path.join(
  root,
  "n00-cortex",
  "data",
  "dependency-overrides",
);

const normalizeNode = (v) => v?.trim();
const isLtsAlias = (v) => /^lts\b/i.test(v || "");
const semverMajor = (v) => {
  const match = (v || "").match(/(\d+)\.(\d+)\.(\d+)/);
  return match ? Number(match[1]) : null;
};
const nodeMatches = (nvmVal, expectedVal) => {
  if (!nvmVal || !expectedVal) return false;
  if (nvmVal === expectedVal) return true;
  // Treat lts/* as satisfying a concrete expected version and vice‑versa,
  // as long as the major versions align (avoids churn when LTS patches bump).
  if (isLtsAlias(nvmVal) && semverMajor(expectedVal)) return true;
  if (isLtsAlias(expectedVal) && semverMajor(nvmVal)) return true;
  return false;
};

const rootNvmrc = normalizeNode(
  fs.readFileSync(path.join(root, ".nvmrc"), "utf8"),
);
const issues = [];
if (!nodeMatches(rootNvmrc, expectedNode)) {
  issues.push(`root .nvmrc (${rootNvmrc}) != manifest node (${expectedNode})`);
}

function readPackageJson(pkgPath) {
  if (!fs.existsSync(pkgPath)) return null;
  try {
    return JSON.parse(fs.readFileSync(pkgPath, "utf8"));
  } catch (_e) {
    return null;
  }
}

function parsePnpmVersion(pkgMgr) {
  if (!pkgMgr) return null;
  const match = pkgMgr.match(/pnpm@(.*)$/);
  return match ? match[1] : null;
}

const versionAccepts = (val, expected) => {
  if (!val || !expected) return false;
  if (val === expected) return true;
  if (val.startsWith(">=") && val.replace(">=", "").trim() === expected)
    return true;
  if (val.startsWith("^") && val.replace("^", "").trim() === expected)
    return true;
  return false;
};

function loadWorkspacePaths() {
  const paths = new Set(["."]); // include workspace root
  // add submodules from .gitmodules
  const gitmodules = path.join(root, ".gitmodules");
  if (fs.existsSync(gitmodules)) {
    const content = fs.readFileSync(gitmodules, "utf8");
    for (const line of content.split(/\r?\n/)) {
      const m = line.match(/^\s*path\s*=\s*(.+)$/);
      if (m) paths.add(m[1].trim());
    }
  }
  // add repos from workspace manifest (covers non-submodule roots)
  if (fs.existsSync(workspaceManifestPath)) {
    try {
      const manifestData = JSON.parse(
        fs.readFileSync(workspaceManifestPath, "utf8"),
      );
      for (const repo of manifestData.repos || []) {
        if (repo.path) paths.add(repo.path);
      }
    } catch (_e) {
      issues.push("failed to parse automation/workspace.manifest.json");
    }
  }
  return Array.from(paths);
}

const paths = loadWorkspacePaths();

function readOverridePython(repo) {
  const overridePath = path.join(overrideDir, `${repo}.json`);
  if (!fs.existsSync(overridePath)) return null;
  try {
    const data = JSON.parse(fs.readFileSync(overridePath, "utf8"));
    const entry = (data.overrides || {}).python;
    if (entry && typeof entry.version === "string") {
      return entry.version.trim();
    }
  } catch (_e) {
    issues.push(`failed to parse python override for ${repo}`);
  }
  return null;
}

for (const p of paths) {
  const pkgPath = path.join(root, p, "package.json");
  const pkg = readPackageJson(pkgPath);
  const pkgMgr = pkg?.packageManager || null;
  const pnpmVersion = parsePnpmVersion(pkgMgr);
  if (pkgMgr && !pnpmVersion) {
    issues.push(
      `${p || "workspace root"} packageManager is not pnpm: ${pkgMgr}`,
    );
  }
  if (pnpmVersion && pnpmVersion !== expectedPnpm) {
    issues.push(
      `${p || "workspace root"} packageManager pnpm@${pnpmVersion} != ${expectedPnpm}`,
    );
  }
  if (pkg && pkg.engines) {
    if (pkg.engines.node && !versionAccepts(pkg.engines.node, expectedNode)) {
      issues.push(
        `${p || "workspace root"} engines.node ${pkg.engines.node} != ${expectedNode}`,
      );
    }
    if (pkg.engines.pnpm && !versionAccepts(pkg.engines.pnpm, expectedPnpm)) {
      issues.push(
        `${p || "workspace root"} engines.pnpm ${pkg.engines.pnpm} != ${expectedPnpm}`,
      );
    }
  }
  const nvmPath = path.join(root, p, ".nvmrc");
  if (fs.existsSync(nvmPath)) {
    const val = normalizeNode(fs.readFileSync(nvmPath, "utf8"));
    if (!nodeMatches(val, expectedNode)) {
      issues.push(`${p || "workspace root"} .nvmrc ${val} != ${expectedNode}`);
    }
  }
  const pythonPath = path.join(root, p, ".python-version");
  if (expectedPython) {
    const overridePython = readOverridePython(p) || expectedPython;
    if (fs.existsSync(pythonPath)) {
      const val = fs.readFileSync(pythonPath, "utf8").trim();
      if (val !== overridePython) {
        issues.push(
          `${p || "workspace root"} .python-version ${val} != ${overridePython}`,
        );
      }
    }
  }
}

const failed = issues.length > 0;
if (failed) {
  log("error", "Toolchain pin mismatches detected", { issues });
} else {
  log(
    "info",
    `Toolchain pins OK (Node ${expectedNode}, pnpm ${expectedPnpm})`,
    {
      node: expectedNode,
      pnpm: expectedPnpm,
    },
  );
}

if (asJson) {
  console.log(
    JSON.stringify({
      ok: !failed,
      issues,
      node: expectedNode,
      pnpm: expectedPnpm,
    }),
  );
}

if (webhook) {
  const desc = failed
    ? issues.join("\n")
    : `Node ${expectedNode}, pnpm ${expectedPnpm}`;
  await notifyDiscord({
    webhook,
    title: failed ? "❌ Toolchain pin check failed" : "✅ Toolchain pins ok",
    description: desc,
    color: failed ? 15158332 : 3066993,
  });
}

if (failed) process.exit(1);
