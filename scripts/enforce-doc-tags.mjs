#!/usr/bin/env node
/**
 * Ensure every Antora page has :page-tags: and :reviewed:.
 * Inserts defaults if missing and updates :reviewed: to today in autofix mode.
 *
 * Defaults: diataxis:reference, domain:platform, audience:contrib, stability:beta
 */
import { globSync } from "glob";
import fs from "node:fs";

const args = process.argv.slice(2);
const dryRun = args.includes("--dry-run");
const rootArg = args.find((a) => a.startsWith("--root="));
const root = rootArg ? rootArg.split("=")[1] : ".";
const today = new Date().toISOString().slice(0, 10);

const files = globSync(`${root}/docs/**/*.adoc`, {
  ignore: [
    "**/partials/**",
    "**/build/**",
    "**/logs/**",
    "**/.cache/**",
    "**/node_modules/**",
  ],
});

let changed = 0;
for (const file of files) {
  const lines = fs.readFileSync(file, "utf8").split("\n");
  let hasTags = lines.some((l) => l.startsWith(":page-tags:"));
  let hasReviewed = lines.some((l) => l.startsWith(":reviewed:"));

  const insertAt = lines.findIndex((l) => l.trim().startsWith("="));
  if (insertAt === -1) continue;

  const inserts = [];
  if (!hasTags) {
    inserts.push(
      `:page-tags: diataxis:reference, domain:platform, audience:contrib, stability:beta`,
    );
  }
  if (!hasReviewed) {
    inserts.push(`:reviewed: ${today}`);
  }

  if (inserts.length === 0) continue;

  const nextLines = [
    ...lines.slice(0, insertAt),
    ...inserts,
    ...lines.slice(insertAt),
  ];

  if (dryRun) {
    console.log(
      `[dry-run] Would patch ${file} -> add ${inserts.length} fields`,
    );
  } else {
    fs.writeFileSync(file, nextLines.join("\n"), "utf8");
    console.log(`[patched] ${file} (+${inserts.length} fields)`);
    changed++;
  }
}

console.log(
  `enforce-doc-tags: changed ${changed} file(s)${dryRun ? " (dry)" : ""}`,
);
