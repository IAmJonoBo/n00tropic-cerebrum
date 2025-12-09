#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
const outFlagIndex = args.findIndex((a) => a === "--output" || a === "-o");
const outputPath =
  outFlagIndex >= 0 && args[outFlagIndex + 1]
    ? path.resolve(args[outFlagIndex + 1])
    : null;

import { fileURLToPath } from "node:url";

const workspaceRoot = path.resolve(
  path.join(path.dirname(fileURLToPath(import.meta.url)), ".."),
);
const manifestPath = path.join(
  workspaceRoot,
  "n00t",
  "capabilities",
  "manifest.json",
);

function readJsonSafe(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch (error) {
    console.error(
      `[capability-health] Failed to read ${filePath}: ${error.message}`,
    );
    process.exit(1);
  }
}

function checkEntrypoint(entrypoint) {
  if (!entrypoint)
    return { exists: false, executable: false, reason: "entrypoint missing" };
  const fullPath = path.resolve(
    path.join(path.dirname(manifestPath), entrypoint),
  );
  const exists = fs.existsSync(fullPath);
  const executable = exists
    ? (fs.statSync(fullPath).mode & 0o111) !== 0
    : false;
  return { exists, executable, fullPath };
}

const manifest = readJsonSafe(manifestPath);
const capabilities = Array.isArray(manifest?.capabilities)
  ? manifest.capabilities
  : [];

const report = {
  generated_at: new Date().toISOString(),
  manifest: path.relative(workspaceRoot, manifestPath),
  total: capabilities.length,
  capabilities: [],
};

for (const cap of capabilities) {
  const entrypointInfo = checkEntrypoint(cap.entrypoint);
  const issues = [];
  if (!entrypointInfo.exists) issues.push("entrypoint_missing");
  else if (!entrypointInfo.executable) issues.push("entrypoint_not_executable");

  const status =
    issues.length === 0
      ? "ok"
      : issues.includes("entrypoint_missing")
        ? "error"
        : "warning";

  report.capabilities.push({
    id: cap.id,
    summary: cap.summary,
    entrypoint: cap.entrypoint,
    entrypoint_full_path: entrypointInfo.fullPath,
    exists: entrypointInfo.exists,
    executable: entrypointInfo.executable,
    issues,
    status,
    tags: cap.metadata?.tags || cap.tags || [],
    owner: cap.metadata?.owner,
  });
}

if (outputPath) {
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, JSON.stringify(report, null, 2));
  console.log(`[capability-health] Wrote ${outputPath}`);
} else {
  console.log(JSON.stringify(report, null, 2));
}
