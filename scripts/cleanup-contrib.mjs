#!/usr/bin/env node
import fs from "fs";
import path from "path";

const filePath = path.resolve(process.cwd(), "n00menon", "CONTRIBUTING.md");
if (!fs.existsSync(filePath)) {
  console.error("File not found:", filePath);
  process.exit(2);
}

const content = fs.readFileSync(filePath, "utf8");
// Normalize CRLF and trim
const normalized = content.replace(/\r\n/g, "\n").trim();

// Find the first heading and keep content until the first duplicate heading
const lines = normalized.split("\n");
const firstIndex = lines.findIndex((l) =>
  l.match(/^#\s+Contributing to n00menon$/i),
);
if (firstIndex === -1) {
  console.error(
    'No "Contributing to n00menon" heading found in file. No changes made.',
  );
  process.exit(1);
}

// Build the result by taking the first block up to the first blank line after the list
// or until the end of file. We assume the first instance contains canonical content.
let endIndex = lines.length;
// look for the line 'For more guidance' which we use as anchor
for (let i = firstIndex; i < lines.length; i++) {
  if (lines[i].includes("For more guidance")) {
    endIndex = i + 1; // include this line
    break;
  }
}

const deduped = lines.slice(firstIndex, endIndex).join("\n") + "\n";
fs.writeFileSync(filePath, deduped, "utf8");
console.log("Cleaned CONTRIBUTING.md (replaced content from", filePath, ")");
process.exit(0);
