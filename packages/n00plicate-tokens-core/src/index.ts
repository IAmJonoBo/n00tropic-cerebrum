import type {
	DesignToken,
	TokenRegistry,
	TokenTheme,
} from "@n00plicate/design-tokens";
import { buildThemeRegistry, registryFrom } from "@n00plicate/design-tokens";
import type { DeepPartial } from "@n00plicate/shared-utils";
import { invariant, memoize } from "@n00plicate/shared-utils";

export interface ThemeDefinition<T = string> {
	name: string;
	groups: TokenTheme<T>["groups"];
	metadata?: Record<string, unknown>;
	extends?: string;
}

export interface ThemeRuntime<T = string> {
	name: string;
	registry: TokenRegistry<T>;
	metadata: Record<string, unknown>;
	parent?: string;
}

const buildRegistryFromDefinition = <T>(
	definition: ThemeDefinition<T>,
): TokenRegistry<T> =>
	buildThemeRegistry({ name: definition.name, groups: definition.groups });

export const resolveThemeGraph = <T>(definitions: ThemeDefinition<T>[]) => {
	const lookup = new Map<string, ThemeDefinition<T>>();
	definitions.forEach((definition) => {
		lookup.set(definition.name, definition);
	});

	const resolve = memoize((name: string): ThemeRuntime<T> => {
		const definition = lookup.get(name);
		invariant(definition, `Unknown theme: ${name}`);

		const registry = buildRegistryFromDefinition(definition);
		if (!definition.extends) {
			return {
				name: definition.name,
				registry,
				metadata: { ...definition.metadata },
			};
		}

		const parent = resolve(definition.extends);
		const mergedRegistry = registryFrom<T>(
			...parent.registry.list(),
			...registry.list(),
		);
		const metadata = {
			...parent.metadata,
			...(definition.metadata ?? {}),
		};
		return {
			name: definition.name,
			registry: mergedRegistry,
			metadata,
			parent: parent.name,
		};
	});

	return definitions.map((definition) => resolve(definition.name));
};

export interface SnapshotOptions {
	includeDiff?: boolean;
	baseline?: string;
}

export interface ThemeSnapshot<T = string> {
	name: string;
	metadata: Record<string, unknown>;
	tokens: Record<string, DesignToken<T>>;
	diff?: {
		added: string[];
		removed: string[];
		changed: string[];
	};
}

export const snapshotThemes = <T>(
	definitions: ThemeDefinition<T>[],
	options: SnapshotOptions = {},
) => {
	const runtimes = resolveThemeGraph(definitions);
	const snapshots: ThemeSnapshot<T>[] = [];
	const baseline = options.baseline
		? runtimes.find((runtime) => runtime.name === options.baseline)
		: undefined;

	runtimes.forEach((runtime) => {
		const snapshot: ThemeSnapshot<T> = {
			name: runtime.name,
			metadata: runtime.metadata,
			tokens: runtime.registry.toJSON(),
		};

		if (options.includeDiff && baseline) {
			const diff = baseline.registry.list().reduce(
				(acc, token) => {
					const candidate = runtime.registry.get(token.name);
					if (!candidate) {
						acc.removed.push(token.name);
					} else if (candidate.value !== token.value) {
						acc.changed.push(token.name);
					}
					return acc;
				},
				{
					added: [] as string[],
					removed: [] as string[],
					changed: [] as string[],
				},
			);
			runtime.registry.list().forEach((token) => {
				if (!baseline.registry.get(token.name)) {
					diff.added.push(token.name);
				}
			});
			snapshot.diff = diff;
		}

		snapshots.push(snapshot);
	});

	return snapshots;
};

export const applyOverrides = <T>(
	definition: ThemeDefinition<T>,
	overrides: DeepPartial<ThemeDefinition<T>>,
): ThemeDefinition<T> => {
	const merged: ThemeDefinition<T> = {
		...definition,
		...overrides,
		groups:
			(overrides.groups as ThemeDefinition<T>["groups"] | undefined) ??
			definition.groups,
		metadata: definition.metadata
			? { ...definition.metadata, ...(overrides.metadata ?? {}) }
			: { ...(overrides.metadata ?? {}) },
	};
	return merged;
};

export const toCombinedThemes = <T>(definitions: ThemeDefinition<T>[]) =>
	definitions.reduce<Record<string, TokenRegistry<T>>>((acc, definition) => {
		acc[definition.name] = buildRegistryFromDefinition(definition);
		return acc;
	}, {});
