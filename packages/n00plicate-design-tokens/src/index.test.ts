import { describe, expect, it } from "vitest";
import type { TokenGroup } from "./index.js";
import {
	combineThemes,
	createTokenRegistry,
	diffRegistries,
	mergeTokenRegistries,
	mergeTokenThemes,
	registryFrom,
} from "./index.js";

describe("design tokens", () => {
	it("builds registries from objects", () => {
		const registry = registryFrom({ primary: "#000" }, { secondary: "#fff" });
		expect(registry.list()).toHaveLength(2);
		expect(registry.get("primary")?.value).toBe("#000");
	});

	it("diffs registries", () => {
		const baseline = registryFrom({ primary: "#000", spacing: "8px" });
		const comparison = registryFrom({ primary: "#111", accent: "#f0f" });
		const diff = diffRegistries(baseline, comparison);
		expect(diff.added.map((token) => token.name)).toEqual(["accent"]);
		expect(diff.removed.map((token) => token.name)).toEqual(["spacing"]);
		expect(diff.changed[0].token.name).toBe("primary");
	});

	it("merges theme definitions", () => {
		const base: TokenGroup[] = [
			{ name: "brand", tokens: [{ name: "primary", value: "#000" }] },
		];
		const dark: TokenGroup[] = [
			{ name: "brand", tokens: [{ name: "primary", value: "#111" }] },
		];
		const merged = mergeTokenThemes(
			{ name: "brand", groups: base },
			{ name: "brand", groups: dark },
		);
		expect(merged.groups[0].tokens?.[0].value).toBe("#111");
	});

	it("builds named registries for each theme", () => {
		const themes = combineThemes([
			{
				name: "light",
				groups: [
					{ name: "brand", tokens: [{ name: "primary", value: "#fff" }] },
				],
			},
			{
				name: "dark",
				groups: [
					{ name: "brand", tokens: [{ name: "primary", value: "#000" }] },
				],
			},
		]);
		expect(Object.keys(themes)).toEqual(["light", "dark"]);
		expect(themes.light.get("primary")?.value).toBe("#fff");
	});

	it("merges registries", () => {
		const first = createTokenRegistry([{ name: "primary", value: "#000" }]);
		const second = createTokenRegistry([{ name: "secondary", value: "#fff" }]);
		const merged = mergeTokenRegistries(first, second);
		expect(merged.list()).toHaveLength(2);
	});
});
