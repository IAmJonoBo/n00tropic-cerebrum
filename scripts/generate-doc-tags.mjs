#!/usr/bin/env node
/**
 * Suggest :page-tags: based on path heuristics and existing tags.
 * Does not write files; prints suggestions.
 */
import { globSync } from "glob";
import fs from "node:fs";
import path from "node:path";

const files = globSync("docs/modules/**/pages/**/*.adoc", {
  ignore: ["**/partials/**", "**/build/**", "**/.cache/**", "**/logs/**"],
});

const inferDomain = (p) => {
  const lower = p.toLowerCase();
  if (lower.includes("brand") || lower.includes("creative") || lower.includes("design")) return "domain:brand";
  if (lower.includes("platform") || lower.includes("infra") || lower.includes("ops")) return "domain:platform";
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
  if (name.includes("explain") || name.includes("overview") || name.includes("adr")) return "diataxis:explanation";
  return "diataxis:reference";
};

for (const f of files) {
  const content = fs.readFileSync(f, "utf8");
  const tagsLine = content.split("\n").find((l) => l.startsWith(":page-tags:"));
  if (tagsLine) continue;
  const inferred = [
    inferDiataxis(f),
    inferDomain(f),
    inferAudience(f),
    "stability:beta",
  ];
  console.log(`${f}: ${inferred.join(", ")}`);
}
