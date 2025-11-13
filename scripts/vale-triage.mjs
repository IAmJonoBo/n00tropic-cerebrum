import { execSync } from "node:child_process";
import fs from "node:fs";

try {
  const useFull = process.argv.includes("--full") || process.env.FULL === "1";
  const cmd = useFull
    ? "vale --output=JSON --ignore-syntax docs"
    : "VALE_LOCAL=1 vale --config .vale.local.ini --output=JSON --ignore-syntax docs";
  console.log("Running:", cmd);
  let out = "";
  try {
    out = execSync(cmd, {
      encoding: "utf8",
      stdio: ["pipe", "pipe", "inherit"],
    });
  } catch (err) {
    // Vale returns non-zero when it finds issues; try to parse stdout from the error
    if (err.stdout) {
      out = err.stdout.toString();
    } else {
      throw err;
    }
  }
  const parsed = JSON.parse(out || "{}");
  const report = {};
  for (const [file, issues] of Object.entries(parsed)) {
    report[file] = {};
    for (const i of issues) {
      const check = i.Check || "unknown";
      report[file][check] = report[file][check] || 0;
      report[file][check] += 1;
    }
  }
  console.log("Vale triage report:");
  for (const f of Object.keys(report)) {
    console.log(`\n${f}`);
    for (const [check, count] of Object.entries(report[f])) {
      console.log(`  ${check}: ${count}`);
    }
  }
  // Save report
  fs.writeFileSync(
    "artifacts/vale-triage.json",
    JSON.stringify(report, null, 2),
  );
} catch (err) {
  console.error("vale triage encountered an error:");
  console.error(err.message || err);
}
