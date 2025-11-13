#!/usr/bin/env node
import fs from "fs";
import path from "path";

const root = process.cwd();
const args = process.argv.slice(2);
const apply = args.includes("--apply");
const dryRun = args.includes("--dry-run");
const dirsArg = args.find((a) => a.startsWith("--dirs="));
const includeDirs = dirsArg
  ? dirsArg
      .split("=")[1]
      .split(",")
      .map((s) => s.trim())
  : null;
const excludeArg = args.find((a) => a.startsWith("--exclude="));
const excludeDirs = excludeArg
  ? excludeArg
      .split("=")[1]
      .split(",")
      .map((s) => s.trim())
  : [];

function walk(dir) {
  const files = [];
  for (const file of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, file.name);
    if (file.isDirectory()) {
      if (
        [
          "node_modules",
          ".git",
          "build",
          "artifacts",
          "vendor",
          ".cache",
          ".gradle",
          ".pnpm",
        ].includes(file.name)
      )
        continue;
      if (excludeDirs.includes(file.name)) continue;
      files.push(...walk(full));
    } else {
      files.push(full);
    }
  }
  return files;
}

let files = walk(root).filter(
  (f) =>
    f.endsWith(".md") ||
    f.endsWith(".adoc") ||
    f.endsWith(".yml") ||
    f.endsWith(".yaml") ||
    f.endsWith(".json") ||
    f.endsWith(".sh") ||
    f.endsWith(".mjs") ||
    f.endsWith(".js") ||
    f.endsWith(".ts"),
);
if (includeDirs) {
  files = files.filter((f) =>
    includeDirs.some(
      (d) =>
        f.includes(`/${d}/`) ||
        f.endsWith(`/${d}`) ||
        f.startsWith(`${root}/${d}/`),
    ),
  );
}
if (excludeDirs.length) {
  files = files.filter(
    (f) =>
      !excludeDirs.some(
        (d) =>
          f.includes(`/${d}/`) ||
          f.endsWith(`/${d}`) ||
          f.startsWith(`${root}/${d}/`),
      ),
  );
}
const replacements = [];
for (const f of files) {
  const content = fs.readFileSync(f, "utf8");
  // Match npx as a whole word (\bnpx\b) to avoid partial matches and
  // handle cases like `npx`, `npx)`, `npx.` and backtick-wrapped code blocks.
  if (/\bnpx\b/.test(content)) {
    const newContent = content.replace(/\bnpx\b/g, "pnpm dlx");
    if (newContent !== content) {
      replacements.push({ file: f, old: content, new: newContent });
      if (apply) {
        fs.copyFileSync(f, `${f}.bak`);
        fs.writeFileSync(f, newContent, "utf8");
        console.log(`Patched: ${f}`);
      } else {
        console.log(`Would replace npx with pnpm dlx in: ${f}`);
      }
    }
  }
}

if (replacements.length === 0) {
  console.log("No `npx` occurrences found for replacement.");
} else {
  console.log(
    `Processed ${replacements.length} files. ${apply ? "Applied" : "Dry-run (no changes)"}.`,
  );
}

if (!apply && replacements.length > 0) process.exit(2);
process.exit(0);
