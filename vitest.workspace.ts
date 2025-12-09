import { defineWorkspace } from "vitest/config";

// Explicit workspace list to stop the extension from auto-scanning dozens of configs.
export default defineWorkspace([
  "n00t/vitest.config.ts",
  "n00-cortex/vitest.config.ts",
  "n00-frontiers/vitest.config.ts",
  "n00plicate/vitest.config.ts",
  "web/vitest.config.ts",
  "mobile/vitest.config.ts",
]);
