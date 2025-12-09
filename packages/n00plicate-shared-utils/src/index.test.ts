import { describe, expect, it } from "vitest";
import { deepMerge, invariant, memoize, stableStringify } from "./index.js";

describe("shared utils", () => {
  it("memoizes expensive calls", () => {
    let runs = 0;
    const sum = memoize((a: number, b: number) => {
      runs += 1;
      return a + b;
    });

    expect(sum(1, 2)).toBe(3);
    expect(sum(1, 2)).toBe(3);
    expect(sum.size()).toBe(1);
    expect(runs).toBe(1);
    sum.clear();
    expect(sum.size()).toBe(0);
    expect(sum(2, 2)).toBe(4);
    expect(runs).toBe(2);
  });

  it("merges deeply nested structures", () => {
    const base = { theme: { primary: "#111111", spacing: [4, 8] } };
    const next = deepMerge(base, {
      theme: { spacing: [4, 12], accent: "#ff00ff" },
    });
    expect(next).toEqual({
      theme: { primary: "#111111", spacing: [4, 12], accent: "#ff00ff" },
    });
    expect(base).toEqual({ theme: { primary: "#111111", spacing: [4, 8] } });
  });

  it("throws informative errors when invariants fail", () => {
    expect(() => invariant(false, "boom")).toThrow(/boom/);
    expect(() => invariant(true, "safe")).not.toThrow();
  });

  it("serializes objects deterministically", () => {
    const first = stableStringify({ b: 2, a: 1 });
    const second = stableStringify({ a: 1, b: 2 });
    expect(first).toBe(second);
  });
});
