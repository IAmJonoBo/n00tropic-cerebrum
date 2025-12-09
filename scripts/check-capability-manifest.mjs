#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(
  path.join(path.dirname(new URL(import.meta.url).pathname), ".."),
);
const manifestPath = path.join(root, "n00t", "capabilities", "manifest.json");

function fail(msg) {
  console.error(`[cap-manifest] ${msg}`);
  process.exitCode = 1;
}

const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
if (!Array.isArray(manifest.capabilities)) fail("capabilities array missing");

const ids = new Set();
for (const cap of manifest.capabilities) {
  if (!cap.id) fail("capability missing id");
  if (ids.has(cap.id)) fail(`duplicate id: ${cap.id}`);
  ids.add(cap.id);
  if (!cap.entrypoint) fail(`capability ${cap.id} missing entrypoint`);
  const epPath = path.resolve(
    path.join(path.dirname(manifestPath), cap.entrypoint),
  );
  if (!fs.existsSync(epPath))
    fail(`capability ${cap.id} entrypoint not found: ${cap.entrypoint}`);
  const mode = fs.statSync(epPath).mode & 0o111;
  if (!mode)
    fail(`capability ${cap.id} entrypoint not executable: ${cap.entrypoint}`);
}

if (process.exitCode) {
  process.exit(process.exitCode);
} else {
  console.log(
    `[cap-manifest] OK (${manifest.capabilities.length} capabilities)`,
  );
}
