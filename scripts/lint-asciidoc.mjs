#!/usr/bin/env node
// Parse AsciiDoc sources with Asciidoctor to catch syntax errors early.

import Asciidoctor from "@asciidoctor/core";
import { globSync } from "glob";
import fs from "node:fs";
import path from "node:path";

const asciidoctor = Asciidoctor();

const roots = ["docs"];
const ignored = [
  "**/build/**",
  "**/logs/**",
  "**/.cache/**",
  "**/node_modules/**",
];

const files = roots
  .flatMap((root) =>
    globSync(`${root}/**/*.adoc`, {
      ignore: ignored,
      nodir: true,
    }),
  )
  .sort();

let failures = 0;
let skipped = 0;

for (const file of files) {
  const content = fs.readFileSync(file, "utf8");
  // Remove Antora resource includes that require the Antora pipeline to resolve
  const sanitized = content
    .split("\n")
    .filter(
      (line) =>
        !line.match(/include::(partial|example|attachment)\$/) &&
        !line.match(/image::(partial|example|attachment)\$/),
    )
    .join("\n");
  try {
    asciidoctor.convert(sanitized, {
      safe: "safe",
      backend: "html5",
      to_file: false,
      mkdirs: false,
      base_dir: path.dirname(file),
    });
  } catch (error) {
    failures += 1;
    console.error(`AsciiDoc parse failed: ${file}\n${error}\n`);
  }
}

if (failures > 0) {
  console.error(
    `AsciiDoc lint failed on ${failures} file(s); sanitized Antora resource includes.`,
  );
  process.exit(1);
}

console.log(
  `AsciiDoc lint passed for ${files.length} file(s); Antora resource includes sanitized.`,
);
