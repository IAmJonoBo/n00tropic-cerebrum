import fs from "node:fs";
import path from "node:path";

import { danger, fail, warn, message, schedule } from "danger";

const mdChanged: string[] = danger.git.modified_files.filter(
  (f: string) => f.endsWith(".adoc") || f.endsWith(".md"),
);

async function checkReviewDates() {
  if (mdChanged.length) {
    message(`Docs changed: ${mdChanged.length} files`);
    // Encourage review date updates when docs change
    for (const f of mdChanged) {
      const file = f as string;
      const content = await danger.github.utils.fileContents(file);
      if (!/^:reviewed:\s?\d{4}-\d{2}-\d{2}/m.test(content)) {
        warn(`Missing :reviewed: date in ${f}`);
      }
      if (!/^:page-tags:\s?.+/m.test(content)) {
        warn(`Missing :page-tags: metadata in ${f}`);
      }
    }
  }
}

async function ensurePlansResolved() {
  const planFiles = danger.git.modified_files.filter((f) =>
    f.endsWith(".plan.md"),
  );
  for (const file of planFiles) {
    const content = await danger.github.utils.fileContents(file);
    if (content.includes("[[RESOLVE]]")) {
      fail(`Resolve outstanding conflicts in ${file} before merging.`);
    }
  }
}

function ensureBriefsHavePlans() {
  const briefCandidates = danger.git.modified_files.filter(
    (f) =>
      f.startsWith("n00-horizons/docs/experiments/") &&
      f.endsWith(".md") &&
      !f.endsWith(".plan.md"),
  );
  for (const brief of briefCandidates) {
    const planPath = brief.replace(/\.md$/, ".plan.md");
    const resolved = path.resolve(process.cwd(), planPath);
    if (!fs.existsSync(resolved)) {
      warn(
        `No companion plan file detected for ${brief}. Generate ${planPath} via n00t plan before merging.`,
      );
    }
  }
}

async function summarizePlanMetrics() {
  const planFiles = danger.git.modified_files.filter((f) =>
    f.endsWith(".plan.md"),
  );
  for (const file of planFiles) {
    const content = await danger.github.utils.fileContents(file);
    const dryMatch = /DRY score:\s*(\d+(?:\.\d+)?)/i.exec(content);
    const yagniMatch = /YAGNI score:\s*(\d+(?:\.\d+)?)/i.exec(content);
    const conflictMatch = /Conflicts:\s*(\d+)/i.exec(content);
    if (!dryMatch || !yagniMatch || !conflictMatch) {
      continue;
    }
    const dryScore = Number.parseFloat(dryMatch[1]);
    const yagniScore = Number.parseFloat(yagniMatch[1]);
    const conflicts = Number.parseInt(conflictMatch[1], 10);
    message(
      `Plan metrics for ${file}: DRY=${dryScore.toFixed(2)} YAGNI=${yagniScore.toFixed(2)} conflicts=${conflicts}`,
    );
    if (yagniScore > 0.3) {
      fail(
        `YAGNI score ${yagniScore.toFixed(2)} exceeds threshold (0.30) for ${file}. Update the plan to remove unnecessary scope.`,
      );
    }
    if (conflicts > 0) {
      fail(
        `Plan ${file} still lists ${conflicts} conflicts. Resolve them or document resolutions before merging.`,
      );
    }
  }
}

function ensureTypesenseFreshness() {
  const logDir = path.join(process.cwd(), "docs/search/logs");
  let entries: { file: string; mtime: number }[] = [];
  try {
    const files = fs
      .readdirSync(logDir)
      .filter((name) => name.endsWith(".log.json"));
    entries = files.map((name) => {
      const full = path.join(logDir, name);
      const stats = fs.statSync(full);
      return { file: full, mtime: stats.mtimeMs };
    });
  } catch (error) {
    warn(
      `Unable to inspect docs/search/logs for Typesense summaries (${String(
        error,
      )}). Run docs/search/scripts/capture-latest-summary.sh once before merging.`,
    );
    return;
  }
  if (!entries.length) {
    fail(
      "Typesense summary (.log.json) not found under docs/search/logs. Run docs/search/scripts/capture-latest-summary.sh (or the docs Typesense recipe) before merging docs/search changes.",
    );
    return;
  }
  entries.sort((a, b) => b.mtime - a.mtime);
  const latest = entries[0];
  let payload: { [key: string]: unknown } = {};
  try {
    payload = JSON.parse(fs.readFileSync(latest.file, "utf8"));
  } catch (error) {
    fail(`Unable to parse Typesense summary ${latest.file}: ${String(error)}`);
    return;
  }
  const capturedRaw = (payload["captured_at"] || payload["capturedAt"]) as
    | string
    | undefined;
  const capturedAt = capturedRaw ? Date.parse(capturedRaw) : NaN;
  if (Number.isNaN(capturedAt)) {
    fail(
      `Typesense summary ${latest.file} is missing a valid captured_at timestamp. Re-run docs/search/scripts/capture-latest-summary.sh.`,
    );
    return;
  }
  const ageMs = Date.now() - capturedAt;
  const maxAgeMs = 7 * 24 * 60 * 60 * 1000;
  if (ageMs > maxAgeMs) {
    const days = (ageMs / (24 * 60 * 60 * 1000)).toFixed(1);
    fail(
      `Typesense index summary is stale (${days} days old). Refresh the index via docs/search/README.adoc (or run docs/search/scripts/capture-latest-summary.sh) before merging.`,
    );
  }
}

schedule(async () => {
  await checkReviewDates();
  await ensurePlansResolved();
  await summarizePlanMetrics();
  ensureBriefsHavePlans();
  ensureTypesenseFreshness();
});
