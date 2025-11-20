import { describe, expect, it } from "vitest";
import {
  applyOverrides,
  resolveThemeGraph,
  snapshotThemes,
  toCombinedThemes,
} from "./index.js";

describe("tokens core", () => {
  const baseDefinition = {
    name: "base",
    groups: [{ name: "brand", tokens: [{ name: "primary", value: "#000" }] }],
    metadata: { description: "Base theme" },
  } as const;

  it("resolves inheritance trees", () => {
    const child = {
      name: "child",
      extends: "base",
      groups: [{ name: "brand", tokens: [{ name: "primary", value: "#111" }] }],
    } as const;
    const runtimes = resolveThemeGraph([baseDefinition, child]);
    const childRuntime = runtimes.find((runtime) => runtime.name === "child");
    expect(childRuntime?.parent).toBe("base");
    expect(childRuntime?.registry.get("primary")?.value).toBe("#111");
  });

  it("applies overrides immutably", () => {
    const overridden = applyOverrides(baseDefinition, {
      metadata: { description: "overridden" },
    });
    expect(overridden.metadata?.description).toBe("overridden");
    expect(baseDefinition.metadata?.description).toBe("Base theme");
  });

  it("produces snapshots with diffs", () => {
    const child = {
      name: "child",
      groups: [{ name: "brand", tokens: [{ name: "accent", value: "#fff" }] }],
    } as const;
    const snapshots = snapshotThemes([baseDefinition, child], {
      includeDiff: true,
      baseline: "base",
    });
    const childSnapshot = snapshots.find(
      (snapshot) => snapshot.name === "child",
    );
    expect(childSnapshot?.diff?.added).toContain("accent");
    expect(childSnapshot?.diff?.removed).toContain("primary");
  });

  it("exposes a combined theme map", () => {
    const map = toCombinedThemes([baseDefinition]);
    expect(map.base.get("primary")?.value).toBe("#000");
  });
});
