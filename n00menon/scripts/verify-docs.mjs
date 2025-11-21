#!/usr/bin/env node
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const pagesPath = path.join(root, "modules", "ROOT", "pages");
const navPath = path.join(root, "modules", "ROOT", "nav.adoc");

let ok = true;
if (!fs.existsSync(pagesPath)) {
  console.error("ERROR: pages directory missing:", pagesPath);
  ok = false;
}

if (!fs.existsSync(navPath)) {
  console.error("ERROR: nav.adoc missing at:", navPath);
  ok = false;
}

if (ok) {
  console.log("Verified basic docs layout for n00menon");
  process.exit(0);
} else {
  process.exit(2);
}
