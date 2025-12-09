#!/usr/bin/env node
/**
 * Guardrail to keep Node/TypeScript baseline versions in sync across subrepos/templates.
 *
 * What it checks:
 * - n00menon tsconfig extends @tsconfig/node<MAJOR>/tsconfig.json.
 * - n00-frontiers node-service template uses major-only @tsconfig reference.
 * - Node baseline values in cookiecutter.json, manifest.{json,yaml}, and README table
 *   match the expected version.
 *
 * Update EXPECTED_NODE_VERSION when bumping Node; run `pnpm run tsconfig:check`.
 */

import fs from "node:fs";
import path from "node:path";

const EXPECTED_NODE_VERSION = "24.11.0";
const EXPECTED_NODE_MAJOR = EXPECTED_NODE_VERSION.split(".")[0];

const repoRoot = path.resolve(
  path.dirname(decodeURIComponent(new URL(import.meta.url).pathname)),
  "..",
);

function read(file) {
  return fs.readFileSync(path.join(repoRoot, file), "utf8");
}

const checks = [
  {
    file: "n00menon/tsconfig.json",
    test: (s) =>
      s.includes(
        `\"extends\": \"@tsconfig/node${EXPECTED_NODE_MAJOR}/tsconfig.json\"`,
      ),
    message: `n00menon/tsconfig.json should extend @tsconfig/node${EXPECTED_NODE_MAJOR}/tsconfig.json`,
  },
  {
    file: "n00-frontiers/applications/scaffolder/templates/node-service/{{cookiecutter.project_slug}}/tsconfig.json",
    test: (s) =>
      /@tsconfig\/node\{\{\s*cookiecutter\.node_version\.split\('\.'\)\[0\]\s*\}\}\/tsconfig\.json/.test(
        s,
      ),
    message:
      "node-service template tsconfig should reference @tsconfig/node<major>/tsconfig.json using cookiecutter.node_version.split()[0]",
  },
  {
    file: "n00-frontiers/applications/scaffolder/templates/node-service/cookiecutter.json",
    test: (s) => JSON.parse(s).node_version === EXPECTED_NODE_VERSION,
    message: `cookiecutter.json node_version should be ${EXPECTED_NODE_VERSION}`,
  },
  {
    file: "n00-frontiers/applications/scaffolder/templates/manifest.json",
    test: (s) => {
      const data = JSON.parse(s);
      return (
        data.templates?.["node-service"]?.sample_contexts?.default
          ?.node_version === EXPECTED_NODE_VERSION
      );
    },
    message: `manifest.json node-service sample_contexts.default.node_version should be ${EXPECTED_NODE_VERSION}`,
  },
  {
    file: "n00-frontiers/applications/scaffolder/templates/manifest.yaml",
    test: (s) =>
      new RegExp(`node_version:\\s*\"?${EXPECTED_NODE_VERSION}\"?`).test(s),
    message: `manifest.yaml node_version should be ${EXPECTED_NODE_VERSION}`,
  },
  {
    file: "n00-frontiers/applications/scaffolder/templates/node-service/README.md",
    test: (s) =>
      s.includes(
        `| \`node_version\`          | 24                           | ${EXPECTED_NODE_VERSION}`,
      ),
    message: `node-service README table should list node_version ${EXPECTED_NODE_VERSION} as default`,
  },
];

let failures = 0;
for (const check of checks) {
  try {
    const content = read(check.file);
    if (!check.test(content)) {
      failures++;
      console.error(`✖ ${check.message}`);
    }
  } catch (err) {
    failures++;
    console.error(`✖ Failed to read ${check.file}: ${err.message}`);
  }
}

if (failures > 0) {
  console.error(`\nFound ${failures} configuration drift issue(s).`);
  process.exit(1);
} else {
  console.log("✓ TypeScript/Node baseline looks consistent.");
}
