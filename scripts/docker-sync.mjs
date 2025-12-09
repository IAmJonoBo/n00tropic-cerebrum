#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import {
  appendFileSync,
  existsSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceRoot = path.resolve(__dirname, "..");

const PENPOT_COMPOSE = path.join(
  workspaceRoot,
  "n00plicate/infra/containers/devcontainer/docker-compose.yml",
);
const PENPOT_UPDATE_SCRIPT = path.join(
  workspaceRoot,
  "n00plicate/scripts/update-penpot-images.mjs",
);
const ERPNEXT_DIR = path.join(
  workspaceRoot,
  "n00tropic_HQ/12-Platform-Ops/erpnext-docker",
);
const ERPNEXT_ENV = path.join(ERPNEXT_DIR, ".env");
const ERPNEXT_COMPOSE = path.join(ERPNEXT_DIR, "docker-compose.yml");
const TELEMETRY_LOG = path.join(
  workspaceRoot,
  "n00tropic_HQ/12-Platform-Ops/telemetry/docker-sync.log",
);

const args = process.argv.slice(2);
const onlyTargets = new Set();
for (let index = 0; index < args.length; index += 1) {
  if (args[index] === "--only") {
    onlyTargets.add(args[index + 1]);
    index += 1;
  }
}

const SEMVER_REGEX = /^v?(\d+)\.(\d+)\.(\d+)$/;
const compareSemver = (a, b) => {
  const matchA = SEMVER_REGEX.exec(a);
  const matchB = SEMVER_REGEX.exec(b);
  if (!matchA || !matchB) {
    return 0;
  }
  for (let i = 1; i <= 3; i += 1) {
    const diff = Number(matchA[i]) - Number(matchB[i]);
    if (diff !== 0) return diff;
  }
  return 0;
};

const findDockerComposeCommand = () => {
  const candidates = [
    { cmd: "docker", args: ["compose", "version"] },
    { cmd: "docker-compose", args: ["version"] },
  ];
  for (const candidate of candidates) {
    const check = spawnSync(candidate.cmd, candidate.args, { stdio: "ignore" });
    if (check.status === 0) {
      return candidate.cmd === "docker"
        ? ["docker", "compose"]
        : ["docker-compose"];
    }
  }
  return null;
};

const dockerComposeCmd = findDockerComposeCommand();

const runComposePull = (composePath, services) => {
  if (!dockerComposeCmd) {
    return { skipped: true, reason: "docker compose not available" };
  }
  const cwd = path.dirname(composePath);
  const fileArg = ["-f", path.basename(composePath), "pull", ...services];
  const result = spawnSync(
    dockerComposeCmd[0],
    [...dockerComposeCmd.slice(1), ...fileArg],
    {
      cwd,
      stdio: "inherit",
      timeout: 60000,
    },
  );
  if (result.error) {
    return { skipped: true, reason: result.error.message };
  }
  return { skipped: false, status: result.status };
};

const readEnvValue = (filePath, key) => {
  if (!existsSync(filePath)) {
    return undefined;
  }
  const content = readFileSync(filePath, "utf8");
  for (const line of content.split(/\r?\n/)) {
    const [k, v] = line.split("=");
    if (k === key) {
      return v?.trim();
    }
  }
  return undefined;
};

const writeEnvValue = (filePath, key, value) => {
  let updated = false;
  let nextLines = [];
  if (existsSync(filePath)) {
    const content = readFileSync(filePath, "utf8");
    nextLines = content
      .split(/\r?\n/)
      .filter((line) => line.length > 0)
      .map((line) => {
        if (line.startsWith(`${key}=`)) {
          updated = true;
          return `${key}=${value}`;
        }
        return line;
      });
  }
  if (!updated) {
    nextLines.push(`${key}=${value}`);
  }
  writeFileSync(filePath, `${nextLines.join("\n")}\n`);
};

const fetchSemverTags = async (repo) => {
  let page = 1;
  const tags = new Set();
  const maxPages = 5;
  while (page <= maxPages) {
    const response = await fetch(
      `https://registry.hub.docker.com/v2/repositories/${repo}/tags?page_size=100&page=${page}&ordering=last_updated`,
    );
    if (!response.ok) {
      throw new Error(
        `Failed to fetch tags for ${repo}: ${response.status} ${response.statusText}`,
      );
    }
    const data = await response.json();
    for (const result of data.results ?? []) {
      if (SEMVER_REGEX.test(result.name)) {
        const normalized = result.name.startsWith("v")
          ? result.name
          : `v${result.name}`;
        tags.add(normalized);
      }
    }
    if (!data.next) break;
    page += 1;
  }
  if (!tags.size) {
    throw new Error(`No semver tags detected for ${repo}`);
  }
  return Array.from(tags);
};

const syncPenpot = async () => {
  const tmpOutput = mkdtempSync(path.join(tmpdir(), "penpot-version-"));
  const outFile = path.join(tmpOutput, "summary.txt");
  const res = spawnSync("node", [PENPOT_UPDATE_SCRIPT, "--output", outFile], {
    cwd: workspaceRoot,
    stdio: "inherit",
  });
  const summary = { component: "penpot", updated: false };
  if (res.status !== 0) {
    summary.error = "update-script-failed";
  } else if (existsSync(outFile)) {
    const entries = readFileSync(outFile, "utf8")
      .split(/\r?\n/)
      .filter(Boolean)
      .map((line) => line.split("="));
    for (const [key, value] of entries) {
      summary[key] = value;
    }
    summary.updated = summary.updated === "true";
  }
  rmSync(tmpOutput, { recursive: true, force: true });
  const pullResult = runComposePull(PENPOT_COMPOSE, [
    "penpot-db",
    "penpot-redis",
    "penpot-backend",
    "penpot-frontend",
    "penpot-export",
  ]);
  return { ...summary, pullResult };
};

const syncErpnext = async () => {
  const tags = await fetchSemverTags("frappe/erpnext-worker");
  const sorted = tags.sort(compareSemver);
  const latest = sorted[sorted.length - 1];
  const current = readEnvValue(ERPNEXT_ENV, "ERPNEXT_VERSION") ?? "v0.0.0";
  const needsUpdate = compareSemver(latest, current) > 0;
  if (needsUpdate) {
    writeEnvValue(ERPNEXT_ENV, "ERPNEXT_VERSION", latest);
  }
  const pullResult = runComposePull(ERPNEXT_COMPOSE, [
    "erpnext-worker",
    "erpnext-scheduler",
    "erpnext-python",
    "erpnext-nginx",
    "mariadb",
    "redis-cache",
    "redis-queue",
    "redis-socketio",
  ]);
  return {
    component: "erpnext",
    current_version: current,
    latest_version: latest,
    updated: needsUpdate,
    pullResult,
  };
};

const appendLog = (entries) => {
  const payload = {
    timestamp: new Date().toISOString(),
    entries,
  };
  appendFileSync(TELEMETRY_LOG, `${JSON.stringify(payload)}\n`);
};

const main = async () => {
  const results = [];
  if (!onlyTargets.size || onlyTargets.has("penpot")) {
    results.push(await syncPenpot());
  }
  if (!onlyTargets.size || onlyTargets.has("erpnext")) {
    results.push(await syncErpnext());
  }
  appendLog(results);
  for (const entry of results) {
    const pullMsg = entry.pullResult?.skipped
      ? `pull skipped (${entry.pullResult.reason})`
      : `docker pull exit=${entry.pullResult.status}`;
    const current = entry.current_version ?? "unknown";
    const latest = entry.latest_version ?? "unknown";
    console.log(
      `${entry.component}: current=${current} latest=${latest} updated=${entry.updated} ${pullMsg}`,
    );
  }
};

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
