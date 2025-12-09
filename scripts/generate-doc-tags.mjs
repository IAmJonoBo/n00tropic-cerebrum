#!/usr/bin/env node
/**
 * Suggest or apply :page-tags: based on path heuristics and existing tags.
 * Use --apply to write inferred tags into files missing :page-tags:.
 */
import { globSync } from "glob";
import fs from "node:fs";
import path from "node:path";

const files = globSync("docs/modules/**/pages/**/*.adoc", {
  ignore: ["**/partials/**", "**/build/**", "**/.cache/**", "**/logs/**"],
});

const apply = process.argv.includes("--apply");
const today = new Date().toISOString().slice(0, 10);

const inferDomain = (p) => {
  const lower = p.toLowerCase();
  if (
    lower.includes("brand") ||
    lower.includes("creative") ||
    lower.includes("design")
  )
    return "domain:brand";
  if (
    lower.includes("platform") ||
    lower.includes("infra") ||
    lower.includes("ops")
  )
    return "domain:platform";
  if (lower.includes("ai") || lower.includes("agent")) return "domain:ai";
  return "domain:platform";
};

const inferAudience = (p) => {
  const lower = p.toLowerCase();
  if (lower.includes("agent")) return "audience:agent";
  if (lower.includes("user")) return "audience:user";
  if (lower.includes("ops")) return "audience:operator";
  return "audience:contrib";
};

const inferDiataxis = (p) => {
  const name = path.basename(p).toLowerCase();
  if (name.includes("howto") || name.includes("guide")) return "diataxis:howto";
  if (name.includes("tutorial")) return "diataxis:tutorial";
  if (
    name.includes("explain") ||
    name.includes("overview") ||
    name.includes("adr")
  )
    return "diataxis:explanation";
  return "diataxis:reference";
};

for (const f of files) {
  const content = fs.readFileSync(f, "utf8");
  const lines = content.split("\n");
  const tagsLineIdx = lines.findIndex((l) => l.startsWith(":page-tags:"));
  if (tagsLineIdx >= 0) continue;
  const inferred = [
    inferDiataxis(f),
    inferDomain(f),
    inferAudience(f),
    "stability:beta",
  ];
  if (apply) {
    const insertAt = lines.findIndex((l) => l.trim().startsWith("="));
    const reviewedIdx = lines.findIndex((l) => l.startsWith(":reviewed:"));
    const newLines = [...lines];
    const tagsLine = `:page-tags: ${inferred.join(", ")}`;
    if (insertAt >= 0) {
      newLines.splice(insertAt, 0, tagsLine);
    } else {
      newLines.unshift(tagsLine);
    }
    if (reviewedIdx === -1) {
      newLines.splice(
        insertAt >= 0 ? insertAt + 1 : 1,
        0,
        `:reviewed: ${today}`,
      );
    }
    fs.writeFileSync(f, newLines.join("\n"), "utf8");
    console.log(`[applied] ${f} -> ${tagsLine}`);
  } else {
    console.log(`${f}: ${inferred.join(", ")}`);
  }
}
