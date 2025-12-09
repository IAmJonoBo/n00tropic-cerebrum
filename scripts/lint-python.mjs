import { spawnSync } from "node:child_process";
import { glob } from "glob";

const PYTHON_CANDIDATES = [process.env.PYTHON_BIN, "python", "python3"].filter(
  Boolean,
);

const ISORT_SKIP = [
  ".cache",
  "node_modules",
  ".trunk",
  ".venv",
  ".venv-workspace",
  "venv",
  "env",
  "n00clear-fusion/.venv",
  "n00clear-fusion/.venv-fusion",
  ".nox",
  ".uv",
  ".uv-cache",
  "bench",
  ".bench",
];

const ISORT_SKIP_GLOB = [
  "**/.venv*/**",
  "**/env/**",
  "**/site-packages/**",
  "**/dist-packages/**",
  "**/__pypackages__/**",
  "**/.nox/**",
  "**/.uv/**",
  "**/.uv-cache/**",
  "**/bench/**",
  "**/.bench/**",
];

const BLACK_EXCLUDE =
  "(node_modules|\\.cache|\\.trunk|\\.venv-workspace|\\.venv|venv|env|n00clear-fusion/.venv-fusion|n00clear-fusion/.venv|\\.nox|\\.uv|\\.uv-cache|bench|\\.bench)";

const RUFF_EXCLUDE = [
  "node_modules",
  "/.cache/",
  ".trunk",
  ".venv",
  ".venv-workspace",
  "venv",
  "env",
  "n00clear-fusion/.venv",
  "n00clear-fusion/.venv-fusion",
  "**/.venv*/**",
  "**/env/**",
  "**/site-packages/**",
  "**/dist-packages/**",
  "**/__pypackages__/**",
  ".nox",
  ".uv",
  ".uv-cache",
  "**/.nox/**",
  "**/.uv/**",
  "**/.uv-cache/**",
  "bench",
  ".bench",
  "**/bench/**",
  "**/.bench/**",
  "**/{{cookiecutter.*}}/**",
].join(",");

function resolvePython() {
  for (const candidate of PYTHON_CANDIDATES) {
    try {
      const res = spawnSync(candidate, ["--version"], {
        encoding: "utf8",
        stdio: ["pipe", "pipe", "ignore"],
      });
      if (res.status === 0) {
        return candidate;
      }
    } catch (_err) {
      // try next candidate
    }
  }
  return null;
}

function run(cmd, args, cwd) {
  console.log(`Running: ${cmd} ${args.join(" ")} ${cwd ? `in ${cwd}` : ""}`);
  const res = spawnSync(cmd, args, {
    encoding: "utf8",
    stdio: "inherit",
    cwd: cwd || process.cwd(),
  });
  return res.status === 0;
}

const pythonCmd = resolvePython();
if (!pythonCmd) {
  console.log(
    "Python not found (checked PYTHON_BIN, python, python3); skipping Python lint checks.",
  );
  process.exit(0);
}

// Find pyproject.toml files in the repository and run checks in their directories
const entries = glob.sync("**/pyproject.toml", {
  ignore: [
    "**/node_modules/**",
    "**/.trunk/**",
    "**/.venv*/**",
    ".venv*/**",
    "**/env/**",
    "env/**",
    "**/site-packages/**",
    "**/dist-packages/**",
    "**/__pypackages__/**",
    "**/.uv/**",
    "**/.nox/**",
    "**/.uv-cache/**",
    "**/bench/**",
    "**/.bench/**",
    "n00-frontiers/templates/**",
    "n00-frontiers/examples/**",
  ],
});
if (entries.length === 0) {
  console.log("No Python projects detected");
  process.exit(0);
}

const args = process.argv.slice(2);
let doFix = false;
let doRuffFix = false;
if (args.includes("--fix")) doFix = true;
if (args.includes("--fix-ruff")) doRuffFix = true;
const runPy = (pyArgs, dir) => run(pythonCmd, pyArgs, dir);

const makeIsortArgs = (checkOnly) => {
  const base = ["-m", "isort", "--profile", "black"];
  if (checkOnly) {
    base.push("--check-only");
  }
  base.push(".");
  ISORT_SKIP.forEach((entry) => {
    base.push("--skip", entry);
  });
  ISORT_SKIP_GLOB.forEach((entry) => {
    base.push("--skip-glob", entry);
  });
  return base;
};

const makeBlackArgs = (checkOnly) => {
  const base = ["-m", "black"];
  if (checkOnly) {
    base.push("--check");
  }
  base.push(".", "--exclude", BLACK_EXCLUDE);
  return base;
};

const makeRuffArgs = (fix) => {
  const base = ["-m", "ruff", "check"];
  if (fix) {
    base.push("--fix");
  }
  base.push(".", "--exclude", RUFF_EXCLUDE);
  return base;
};
let overallOk = true;
for (const p of entries) {
  const dir =
    p.replace("/pyproject.toml", "").replace("pyproject.toml", ".") || ".";
  console.log("\n== Running Python linters in", dir);
  let ok = true;
  // isort: run fix if requested; otherwise check only
  if (doFix) {
    ok = runPy(makeIsortArgs(false), dir) && ok;
  } else {
    ok = runPy(makeIsortArgs(true), dir) && ok;
  }
  // black: run fix if requested; otherwise check only
  if (doFix) {
    ok = runPy(makeBlackArgs(false), dir) && ok;
  } else {
    ok = runPy(makeBlackArgs(true), dir) && ok;
  }
  // ruff check: optionally attempt an auto-fix (conservative)
  if (doRuffFix) {
    ok = runPy(makeRuffArgs(true), dir) && ok;
  } else {
    ok = runPy(makeRuffArgs(false), dir) && ok;
  }
  overallOk = overallOk && ok;
}

if (!overallOk) {
  console.error("\nOne or more Python lint checks failed");
  process.exit(1);
}

console.log("\nPython lint checks passed successfully");
process.exit(0);
