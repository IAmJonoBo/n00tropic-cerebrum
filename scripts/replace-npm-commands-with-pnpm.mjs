#!/usr/bin/env node
// Replacer: replace CLI examples like `npm install` or `npm start` in docs with pnpm equivalents
// Safe-hits: `npm install` -> `pnpm install`, `npm start` -> `pnpm start`, `npm run` -> `pnpm run`, `npm ci` -> `pnpm install --frozen-lockfile` (or `pnpm ci` when supported), `npm test` -> `pnpm test`

import fs from "fs";
import path from "path";

const argv = process.argv.slice(2);
const options = {
  dirs: [],
  exclude: [],
  dryRun: false,
  apply: false,
  backup: true,
};

// Parse args
argv.forEach((a) => {
  if (a.startsWith("--dirs="))
    options.dirs = a
      .replace("--dirs=", "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  else if (a.startsWith("--exclude="))
    options.exclude = a
      .replace("--exclude=", "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  else if (a === "--dry-run") options.dryRun = true;
  else if (a === "--apply") options.apply = true;
  else if (a === "--no-backup") options.backup = false;
});

if (!options.dirs.length) {
  console.error("No dirs provided. Use --dirs=dir1,dir2");
  process.exit(1);
}

const exts = [".md", ".adoc", ".txt", ".yml", ".yaml", ".json", ".sh"];

const replacePatterns = [
  { regex: /\bnpm\s+install\b/g, replace: "pnpm install" },
  { regex: /\bnpm\s+ci\b/g, replace: "pnpm install --frozen-lockfile" },
  { regex: /\bnpm\s+start\b/g, replace: "pnpm start" },
  { regex: /\bnpm\s+run\b/g, replace: "pnpm run" },
  { regex: /\bnpm\s+test\b/g, replace: "pnpm test" },
];

function shouldExclude(filePath) {
  for (const ex of options.exclude) {
    if (!ex) continue;
    if (filePath.includes(path.join(ex))) return true;
    if (filePath.includes(`/${ex}/`)) return true;
  }
  return false;
}

function processFile(filePath) {
  if (shouldExclude(filePath)) return null;
  if (!exts.includes(path.extname(filePath))) return null;
  const content = fs.readFileSync(filePath, "utf8");
  let patched = content;
  let changed = false;
  replacePatterns.forEach(({ regex, replace }) => {
    // Only replace if the line doesn't already contain a pnpm equivalent
    const lines = patched.split("\n");
    let newLines = lines.map((line) => {
      if (line.includes("pnpm")) return line;
      if (regex.test(line)) return line.replace(regex, replace);
      return line;
    });
    const newContent = newLines.join("\n");
    if (newContent !== patched) {
      patched = newContent;
      changed = true;
    }
  });
  if (changed) {
    if (options.dryRun) {
      return { filePath, before: content, after: patched };
    } else if (options.apply) {
      if (options.backup) fs.writeFileSync(filePath + ".bak", content, "utf8");
      fs.writeFileSync(filePath, patched, "utf8");
      return { filePath, applied: true };
    }
  }
  return null;
}

function walk(dir) {
  const results = [];
  const list = fs.readdirSync(dir);
  // Avoid recursion loops and skip common big dirs
  if (dir.includes("/.git") || dir.includes("/node_modules")) return results;
  list.forEach(function (file) {
    const full = path.join(dir, file);
    const stat = fs.statSync(full);
    if (stat && stat.isDirectory()) {
      if (shouldExclude(full)) return;
      if (stat.isSymbolicLink()) return; // skip symlink dirs to avoid cycles
      results.push(...walk(full));
    } else {
      results.push(full);
    }
  });
  return results;
}

let results = [];
for (const dir of options.dirs) {
  if (!fs.existsSync(dir)) continue;
  const files = walk(dir);
  files.forEach((f) => {
    const res = processFile(f);
    if (res) results.push(res);
  });
}

if (options.dryRun) {
  if (results.length === 0) {
    console.log("No `npm` command occurrences found for replacement.");
    process.exit(0);
  }
  results.forEach((r) => {
    console.log(`Would replace in ${r.filePath}`);
  });
  process.exit(0);
}

if (!options.apply) {
  console.log("No action taken, provide --apply to make changes.");
  process.exit(0);
}

console.log("Applied to files:");
results.forEach((r) => console.log(" -", r.filePath));
