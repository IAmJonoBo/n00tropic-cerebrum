#!/usr/bin/env node
// Check that self-hosted runners exist for the superrepo and each submodule.
// Requires GH_TOKEN with repo scope and the GitHub CLI (`gh`) installed.
import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { log } from "./lib/log.mjs";

function gh(args) {
  return execSync(`gh ${args}`, { encoding: "utf8", stdio: ["pipe", "pipe", "pipe"] });
}

function listRepos() {
  const root = process.cwd();
  const repos = [{ name: path.basename(root), path: "." }];
  const gm = fs.readFileSync(path.join(root, ".gitmodules"), "utf8");
  gm.split(/\r?\n/).forEach((line) => {
    const m = line.match(/^\s*path\s*=\s*(.+)$/);
    if (m) repos.push({ name: m[1].trim(), path: m[1].trim() });
  });
  return repos;
}

const requiredLabels = (process.env.REQUIRED_RUNNER_LABELS || "self-hosted,linux,x64,pnpm,uv")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

function checkRepo(repo) {
  // Expect origin to be GitHub and infer org/name from remote URL.
  const remote = execSync(`git -C ${repo.path} config --get remote.origin.url`, { encoding: "utf8" }).trim();
  const m = remote.match(/github.com[:/]([^/]+)\/([^/.]+)(\.git)?$/);
  if (!m) {
    return { repo: repo.name, status: "unknown remote" };
  }
  const full = `${m[1]}/${m[2]}`;
  try {
    const out = gh(`api repos/${full}/actions/runners`);
    const data = JSON.parse(out);
    const total = data.total_count || 0;
    const labels = new Set();
    (data.runners || []).forEach((r) => (r.labels || []).forEach((l) => labels.add(l.name)));
    const labelList = Array.from(labels).sort();
    const missing = requiredLabels.filter((rl) => !labels.has(rl));
    return { repo: full, total, labels: labelList, missing };
  } catch (e) {
    return { repo: full, status: `error: ${e.message}` };
  }
}

const token = process.env.GH_TOKEN || process.env.GITHUB_TOKEN;
if (!token) {
  log("error", "GH_TOKEN/GITHUB_TOKEN not set; skipping runner check");
  process.exit(1);
}

const results = listRepos().map(checkRepo);
results.forEach((r) => {
  if (r.status) {
    log("error", `${r.repo}: ${r.status}`);
  } else {
    log("info", `${r.repo}: ${r.total} runners`, { repo: r.repo, total: r.total, labels: r.labels });
    if (r.missing?.length) {
      log("warn", `${r.repo} missing required labels`, { missing: r.missing });
    }
  }
});

const missingCount = results.filter((r) => !r.status && r.total === 0);
const missingLabels = results.filter((r) => !r.status && r.total > 0 && r.missing?.length);
if (missingCount.length || missingLabels.length) {
  if (missingCount.length)
    log("error", "Repos missing self-hosted runners", { repos: missingCount.map((m) => m.repo) });
  if (missingLabels.length)
    missingLabels.forEach((r) => log("error", `${r.repo} missing required labels`, { missing: r.missing }));
  process.exit(1);
}

log("info", "Runner check passed", { repos: results.length });
