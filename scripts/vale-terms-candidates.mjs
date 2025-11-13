#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
let threshold = 3;
let dryRun = false;
let outPath = "artifacts/vale-terms-token-counts.json";
let jsonPath = "artifacts/vale-full.json";
let pattern = "**/*";
let whitelistMode = false;
let whitelistTarget = "vocab"; // 'vocab' or 'terms'
let applyEdits = false;
let interactive = false;
let yesAll = false;
let caseInsensitive = false;
let autoWhitelist = false;
let autoApply = false;
let oxfordMode = false;
for (let i = 0; i < args.length; i++) {
  switch (args[i]) {
    case "--threshold":
      threshold = parseInt(args[++i], 10) || threshold;
      break;
    case "--dry-run":
      dryRun = true;
      break;
    case "--output":
      outPath = args[++i] || outPath;
      break;
    case "--json":
      jsonPath = args[++i] || jsonPath;
      break;
    case "--pattern":
      pattern = args[++i] || pattern;
      break;
    case "--whitelist":
      whitelistMode = true;
      // optional target after flag
      if (args[i + 1] && !args[i + 1].startsWith("--")) {
        whitelistTarget = args[++i] || whitelistTarget;
      }
      break;
    case "--case-insensitive":
      caseInsensitive = true;
      break;
    case "--auto-whitelist":
      autoWhitelist = true;
      whitelistMode = true;
      yesAll = true;
      break;
    case "--auto-apply":
      autoApply = true;
      applyEdits = true;
      yesAll = true;
      break;
    case "--oxford":
      oxfordMode = true;
      break;
    case "--apply-edits":
      applyEdits = true;
      break;
    case "--interactive":
      interactive = true;
      break;
    case "--yes":
      yesAll = true;
      break;
    default:
      // unknown
      break;
  }
}

if (!fs.existsSync(jsonPath)) {
  console.error(
    `Missing ${jsonPath}. Run vale-triage to produce artifacts/vale-full.json first.`,
  );
  process.exit(1);
}

const data = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
const counts = {};
const suggestions = {}; // maps token -> suggested replacement
const fileMap = {}; // token -> { file: count }

const matchesMessage = (issue) => {
  if (issue.Match) return issue.Match;
  if (issue.Message) return issue.Message;
  return null;
};

for (const [file, issues] of Object.entries(data)) {
  // simple pattern matcher: a minimal glob using includes
  if (pattern !== "**/*" && !file.includes(pattern.replace("**/", "")))
    continue;
  for (const issue of issues) {
    if (issue.Check !== "Vale.Terms") continue;
    // try to extract a token; Message frequently has 'Prefer "X"' or similar
    let token = issue.Match || null;
    if (!token && issue.Message) {
      // look for "quoted tokens" or single-word tokens in code-like context
      const m = issue.Message.match(/"([A-Za-z0-9/_\-\.:]+)"/);
      if (m) token = m[1];
      else {
        // fallback: pick the first word with limited length
        const fallback = issue.Message.split(/[\s,:;]+/)
          .slice(0, 3)
          .join(" ");
        token = fallback;
      }
    }
    if (!token) continue;
    const k = String(token).trim();
    counts[k] = (counts[k] || 0) + 1;
    // suggested replacement - try to parse 'Prefer "<suggestion>"' or 'use <suggestion>'
    if (issue.Message) {
      const sm = issue.Message.match(
        /Prefer\s+"([^"]+)"|Use\s+"([^"]+)"|use\s+([a-zA-Z0-9_-]+)/i,
      );
      if (sm) {
        suggestions[k] = suggestions[k] || sm[1] || sm[2] || sm[3];
      }
    }
    fileMap[k] = fileMap[k] || {};
    fileMap[k][file] = (fileMap[k][file] || 0) + 1;
  }
}

let effectiveCounts = counts;
let effectiveSuggestions = suggestions;
let effectiveFileMap = fileMap;
if (caseInsensitive) {
  // merge tokens ignoring case into the lowercase token; keep suggestions for the most frequent variant
  const tmpCounts = {};
  const tmpSuggestions = {};
  const tmpFileMap = {};
  for (const [t, c] of Object.entries(counts)) {
    const key = String(t).toLowerCase();
    tmpCounts[key] = (tmpCounts[key] || 0) + c;
    tmpSuggestions[key] = tmpSuggestions[key] || suggestions[t];
    tmpFileMap[key] = tmpFileMap[key] || {};
    if (fileMap[t]) {
      for (const f of Object.keys(fileMap[t]))
        tmpFileMap[key][f] = (tmpFileMap[key][f] || 0) + fileMap[t][f];
    }
  }
  effectiveCounts = tmpCounts;
  effectiveSuggestions = tmpSuggestions;
  effectiveFileMap = tmpFileMap;
}

const arr = Object.entries(effectiveCounts)
  .map(([t, c]) => ({
    token: t,
    count: c,
    suggestion: effectiveSuggestions[t] || null,
    files: effectiveFileMap[t] || {},
  }))
  .sort((a, b) => b.count - a.count);

// Optionally apply Oxford English stylistic preferences for suggestions
const oxfordMap = {
  color: "colour",
  colors: "colours",
  organization: "organisation",
  organizations: "organisations",
  optimize: "optimise",
  optimization: "optimisation",
  center: "centre",
  license: "licence",
  licenses: "licences",
  dialog: "dialogue",
  catalog: "catalogue",
  program: "programme",
  programs: "programmes",
  behavior: "behaviour",
  behaviors: "behaviours",
};
if (oxfordMode) {
  for (const entry of arr) {
    const lower = String(entry.token).toLowerCase();
    if (!entry.suggestion && oxfordMap[lower]) {
      entry.suggestion = oxfordMap[lower];
    } else if (entry.suggestion) {
      const sLower = String(entry.suggestion).toLowerCase();
      if (oxfordMap[sLower]) entry.suggestion = oxfordMap[sLower];
    }
  }
}

// read existing tokens from vocab and Terms
const existing = new Set();
if (fs.existsSync("styles/n00/vocab.txt")) {
  const txt = fs.readFileSync("styles/n00/vocab.txt", "utf8");
  txt.split(/\r?\n/).forEach((l) => l && existing.add(l.trim()));
}
if (fs.existsSync("styles/n00/Terms.yml")) {
  const txt = fs.readFileSync("styles/n00/Terms.yml", "utf8");
  const tokens = [...txt.matchAll(/"([^\"]+)"/g)].map((m) => m[1]);
  tokens.forEach((t) => existing.add(t));
}
// also check .vale.ini TokenIgnores
if (fs.existsSync(".vale.ini")) {
  const txt = fs.readFileSync(".vale.ini", "utf8");
  const m = txt.match(/TokenIgnores\s*=\s*(.*)/);
  if (m) {
    m[1]
      .split(",")
      .map((s) => s.trim())
      .forEach((t) => t && existing.add(t));
  }
}
// If case-insensitive mode requested, also add lowercase variants to existing set for comparison
if (caseInsensitive) {
  const addLower = [...existing].map((t) => String(t).toLowerCase());
  addLower.forEach((l) => existing.add(l));
}

const candidates = arr.filter(
  (r) => r.count >= threshold && !existing.has(r.token),
);

if (candidates.length === 0) {
  console.log(
    `No Term candidates with threshold ${threshold} (existing tokens filtered).`,
  );
  process.exit(0);
}

if (dryRun) {
  console.log("Dry-run: the following Term candidates would be suggested:");
  for (const c of candidates) {
    console.log(`- ${c.token} (${c.count}) suggestion: ${c.suggestion || "-"}`);
  }
  process.exit(0);
}

// produce output JSON with tokens and suggestions
const out = {
  threshold: threshold,
  candidates: candidates,
};
fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, JSON.stringify(out, null, 2));
console.log(
  `Wrote ${outPath} with ${candidates.length} candidates (threshold ${threshold}).`,
);

// Also produce a text file with tokens to append to Terms.yml or vocab.txt
const lines = candidates.map(
  (c) => `${c.token}  # ${c.count}${c.suggestion ? ` -> ${c.suggestion}` : ""}`,
);
fs.writeFileSync(
  "artifacts/vale-terms-suggestions.txt",
  `${lines.join("\n")}\n`,
);
console.log(
  "Wrote artifacts/vale-terms-suggestions.txt with",
  lines.length,
  "items.",
);

// Helper: simple interactive prompt
const ask = async (question) => {
  if (yesAll) return true;
  if (!interactive) return false;
  const readline = await import("node:readline/promises");
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });
  const answer = (await rl.question(question + " (y/N): "))
    .trim()
    .toLowerCase();
  rl.close();
  return answer === "y" || answer === "yes";
};

// Whitelist mode: append tokens safely to vocab.txt or Terms.yml
const appendToVocab = (tokens) => {
  const pathVocab = "styles/n00/vocab.txt";
  fs.mkdirSync(path.dirname(pathVocab), { recursive: true });
  let existingLines = [];
  if (fs.existsSync(pathVocab))
    existingLines = fs.readFileSync(pathVocab, "utf8").split(/\r?\n/);
  const toAppend = tokens.filter((t) => !existingLines.includes(t));
  if (toAppend.length === 0) {
    console.log("No new vocab terms to append.");
    return [];
  }
  if (dryRun) {
    console.log("Dry-run: would append to vocab:", toAppend);
    return toAppend;
  }
  fs.appendFileSync(pathVocab, `\n${toAppend.join("\n")}\n`);
  console.log(`Appended ${toAppend.length} tokens to ${pathVocab}`);
  return toAppend;
};

const appendToTermsYml = (tokens) => {
  // Very conservative: append tokens to Terms.yml lines as a quoted array entry
  const pathTerms = "styles/n00/Terms.yml";
  if (!fs.existsSync(pathTerms)) {
    console.warn(`${pathTerms} doesn't exist; skipping Terms.yml append.`);
    return [];
  }
  const text = fs.readFileSync(pathTerms, "utf8");
  // locate 'terms:' line
  const m = text.match(/terms:\s*\[([\s\S]*?)\]/);
  if (!m) {
    console.warn(
      `Could not find 'terms:' array in ${pathTerms}; skipping Terms.yml append.`,
    );
    return [];
  }
  const inside = m[1];
  const existingTokens = new Set(
    [...inside.matchAll(/"([^"]+)"/g)].map((mm) => mm[1]),
  );
  const toAppend = tokens.filter((t) => !existingTokens.has(t));
  if (toAppend.length === 0) {
    console.log("No new Terms.yml tokens to append.");
    return [];
  }
  if (dryRun) {
    console.log("Dry-run: would append to Terms.yml:", toAppend);
    return toAppend;
  }
  // Insert before the closing ']' in the match
  const newInside =
    inside +
    (inside.trim().endsWith(",") || inside.trim().endsWith("\n") ? "" : ",") +
    "\n    " +
    toAppend.map((t) => `\"${t}\",`).join("\n    ") +
    "\n  ";
  const newText = text.replace(m[0], `terms: [${newInside}]`);
  fs.writeFileSync(pathTerms, newText);
  console.log(`Appended ${toAppend.length} tokens to ${pathTerms}`);
  return toAppend;
};

// Apply editorial edits conservatively
const escapeRegExp = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const isCodeFenceBegin = (line) =>
  line.trim().startsWith("```") ||
  line.trim().startsWith("----") ||
  line.trim().startsWith("....");
const isAsciiDocIncludeImage = (line) =>
  line.includes("include::") ||
  line.includes("image::") ||
  line.includes("xref:");

const previewEditsForFile = (file, token, replacement) => {
  const txt = fs.readFileSync(file, "utf8");
  const lines = txt.split(/\r?\n/);
  let inCodeBlock = false;
  const re = new RegExp(`\\b${escapeRegExp(token)}\\b`, "g");
  const changed = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (isCodeFenceBegin(line)) inCodeBlock = !inCodeBlock;
    if (inCodeBlock) continue;
    if (isAsciiDocIncludeImage(line)) continue;
    if (re.test(line)) {
      // create preview change
      const newLine = line.replace(re, replacement);
      changed.push({ line: i + 1, before: line, after: newLine });
    }
  }
  return changed;
};

const applyEditsForFile = (file, edits) => {
  if (!edits || edits.length === 0) return false;
  const txt = fs.readFileSync(file, "utf8");
  let lines = txt.split(/\r?\n/);
  for (const e of edits) {
    lines[e.line - 1] = e.after;
  }
  const newTxt = lines.join("\n");
  // backup
  fs.copyFileSync(file, `${file}.bak`);
  fs.writeFileSync(file, newTxt);
  return true;
};

const runWhitelist = async (candidatesList) => {
  const tokens = candidatesList.map((c) => {
    if (oxfordMode) {
      const mapped = oxfordMap[String(c.token).toLowerCase()];
      return mapped || c.token;
    }
    return c.token;
  });
  if (tokens.length === 0) {
    console.log("No tokens to whitelist.");
    return;
  }
  console.log(`Candidates to whitelist (${tokens.length}):`, tokens.join(", "));
  let ok = yesAll;
  if (!ok && interactive) {
    ok = await ask("Append these tokens to the workspace vocab/terms?");
  }
  if (!ok && !yesAll) {
    console.log("Skipping whitelist (no confirmation).");
    return;
  }
  if (whitelistTarget === "terms") {
    appendToTermsYml(tokens);
  } else {
    appendToVocab(tokens);
  }
};

const runApplyEdits = async (candidatesList) => {
  const filesChanged = {};
  for (const c of candidatesList) {
    if (!c.suggestion) continue; // nothing to apply
    for (const f of Object.keys(c.files)) {
      if (!fs.existsSync(f)) continue;
      const edits = previewEditsForFile(f, c.token, c.suggestion);
      if (edits.length === 0) continue;
      filesChanged[f] = filesChanged[f] || [];
      filesChanged[f].push({ token: c.token, suggestion: c.suggestion, edits });
    }
  }
  if (Object.keys(filesChanged).length === 0) {
    console.log(
      "No editorial edits to apply (no suggestions or safe changes).",
    );
    return;
  }
  console.log("Proposed edits (summary):");
  for (const [f, changes] of Object.entries(filesChanged)) {
    console.log(`- ${f}: ${changes.length} token(s)`);
    for (const ch of changes) {
      console.log(
        `  - ${ch.token} -> ${ch.suggestion} (${ch.edits.length} line(s))`,
      );
    }
  }
  let ok = yesAll;
  if (!ok && interactive) {
    ok = await ask(
      "Apply these edits to the repository files? This will create backup files with .bak by path.",
    );
  }
  if (!ok && !yesAll) {
    console.log(
      "Skipping apply edits (no confirmation). Use --yes to bypass prompts.",
    );
    return;
  }
  if (dryRun) {
    console.log("Dry-run: would apply edits but not writing files.");
    return;
  }
  // apply actual edits
  const applied = [];
  for (const [f, changes] of Object.entries(filesChanged)) {
    let appliedAny = false;
    for (const ch of changes) {
      const ok2 = applyEditsForFile(f, ch.edits);
      appliedAny = appliedAny || ok2;
    }
    if (appliedAny) applied.push(f);
  }
  console.log(`Applied edits to ${applied.length} files.`);
  fs.writeFileSync(
    "artifacts/vale-terms-applied.json",
    JSON.stringify({ applied, timestamp: new Date().toISOString() }, null, 2),
  );
};

// If user wants to whitelist or apply edits
(async () => {
  if (whitelistMode) {
    await runWhitelist(candidates);
  }
  if (applyEdits) {
    await runApplyEdits(candidates);
  }
  if (!whitelistMode && !applyEdits) {
    // already wrote output and suggestions; nothing else to do
  }
})();

process.exit(0);
