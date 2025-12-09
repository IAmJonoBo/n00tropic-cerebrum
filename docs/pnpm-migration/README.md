# pnpm migration guide

This document explains pnpm migration steps for maintainers.

Scripts included in this repo under : `find-npm-usages.mjs`, `replace-npx-with-pnpm.mjs`, `replace-npm-commands-with-pnpm.mjs`. Use them to find and apply safe pnpm CLI replacements in docs and scripts.

Recommended steps:

1. Run the scan scripts to identify candidate files (see docs/pnpm-migration/npm-candidates.json).
2. For each submodule that contains candidates, create a PR in that repo to apply safe conversions (docs-only).
3. Add per-repo editors/owners as reviewers before merging.

Command examples (from workspace root):
