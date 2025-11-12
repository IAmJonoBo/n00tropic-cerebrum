import { spawnSync } from "node:child_process";
import { glob } from "glob";

function hasPython() {
  try {
    const res = spawnSync("python", ["--version"], {
      encoding: "utf8",
      stdio: ["pipe", "pipe", "ignore"],
    });
    return res.status === 0;
  } catch (_err) {
    return false;
  }
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

if (!hasPython()) {
  console.log("Python not found in PATH; skipping Python lint checks.");
  process.exit(0);
}

// Find pyproject.toml files in the repository and run checks in their directories
const entries = glob.sync("**/pyproject.toml", {
  ignore: [
    "**/node_modules/**",
    "**/.trunk/**",
    "n00-frontiers/templates/**",
    "n00-frontiers/examples/**",
  ],
});
if (entries.length === 0) {
  console.log("No Python projects detected");
  process.exit(0);
}

let overallOk = true;
for (const p of entries) {
  const dir =
    p.replace("/pyproject.toml", "").replace("pyproject.toml", ".") || ".";
  console.log("\n== Running Python linters in", dir);
  let ok = true;
  // isort check
  ok =
    run(
      "python",
      ["-m", "isort", "--profile", "black", "--check-only", "."],
      dir,
    ) && ok;
  // black check
  ok = run("python", ["-m", "black", "--check", "."], dir) && ok;
  // ruff check
  ok = run("python", ["-m", "ruff", "check", "."], dir) && ok;
  overallOk = overallOk && ok;
}

if (!overallOk) {
  console.error("\nOne or more Python lint checks failed");
  process.exit(1);
}

console.log("\nPython lint checks passed successfully");
process.exit(0);
