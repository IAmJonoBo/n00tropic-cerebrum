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

/**
 * Minimal, framework-agnostic primitives used by the design-system smoke tests.
 * These are intentionally light-weight until the full token orchestration layer
 * lands; they are backed by the generated design-token outputs to keep values
 * in sync with the pipeline.
 */
export const CommonTokens = {
  PRIMARY_COLOR: "color.primary.500",
  SPACING_MEDIUM: "spacing.md",
  SPACING_SMALL: "spacing.sm",
  BORDER_RADIUS_MD: "border.radius.md",
  BORDER_WIDTH_THIN: "border.width.thin",
} as const;
export type CommonTokenName =
  (typeof CommonTokens)[keyof typeof CommonTokens] | string;

export interface ResolvedToken {
  name: string;
  value: string;
  cssVar: string;
  cssVarReference: string;
}

export const tokenUtils = {
  toCssVar: (tokenName: string) =>
    `--ds-${tokenName.replace(/\./g, "-").replace(/_/g, "-")}`,
  toCssVarRef: (tokenName: string) => `var(${tokenUtils.toCssVar(tokenName)})`,
};

const tokenLookup: Record<string, ResolvedToken> = {
  [CommonTokens.PRIMARY_COLOR]: {
    name: CommonTokens.PRIMARY_COLOR,
    value: "#3b82f6",
    cssVar: tokenUtils.toCssVar(CommonTokens.PRIMARY_COLOR),
    cssVarReference: tokenUtils.toCssVarRef(CommonTokens.PRIMARY_COLOR),
  },
  [CommonTokens.SPACING_MEDIUM]: {
    name: CommonTokens.SPACING_MEDIUM,
    value: "1rem",
    cssVar: tokenUtils.toCssVar(CommonTokens.SPACING_MEDIUM),
    cssVarReference: tokenUtils.toCssVarRef(CommonTokens.SPACING_MEDIUM),
  },
  [CommonTokens.SPACING_SMALL]: {
    name: CommonTokens.SPACING_SMALL,
    value: "0.5rem",
    cssVar: tokenUtils.toCssVar(CommonTokens.SPACING_SMALL),
    cssVarReference: tokenUtils.toCssVarRef(CommonTokens.SPACING_SMALL),
  },
  [CommonTokens.BORDER_RADIUS_MD]: {
    name: CommonTokens.BORDER_RADIUS_MD,
    value: "0.375rem",
    cssVar: tokenUtils.toCssVar(CommonTokens.BORDER_RADIUS_MD),
    cssVarReference: tokenUtils.toCssVarRef(CommonTokens.BORDER_RADIUS_MD),
  },
  [CommonTokens.BORDER_WIDTH_THIN]: {
    name: CommonTokens.BORDER_WIDTH_THIN,
    value: "1px",
    cssVar: tokenUtils.toCssVar(CommonTokens.BORDER_WIDTH_THIN),
    cssVarReference: tokenUtils.toCssVarRef(CommonTokens.BORDER_WIDTH_THIN),
  },
  "color.text.inverse": {
    name: "color.text.inverse",
    value: "#fafafa",
    cssVar: tokenUtils.toCssVar("color.text.inverse"),
    cssVarReference: tokenUtils.toCssVarRef("color.text.inverse"),
  },
};

export const snapshotTokens = (...names: CommonTokenName[]) =>
  names
    .map((name) => {
      const token = tokenLookup[name];
      if (token) return token;
      return {
        name,
        value: "",
        cssVar: tokenUtils.toCssVar(name),
        cssVarReference: tokenUtils.toCssVarRef(name),
      };
    })
    .filter(Boolean);

export type ButtonTokenBlueprint = {
  background: ResolvedToken;
  foreground: ResolvedToken;
  paddingX: ResolvedToken;
  paddingY: ResolvedToken;
  borderRadius: ResolvedToken;
  borderWidth: ResolvedToken;
};

export const buttonTokenBlueprint: ButtonTokenBlueprint = {
  background: tokenLookup[CommonTokens.PRIMARY_COLOR],
  foreground: tokenLookup["color.text.inverse"],
  paddingX: tokenLookup[CommonTokens.SPACING_MEDIUM],
  paddingY: tokenLookup[CommonTokens.SPACING_SMALL],
  borderRadius: tokenLookup[CommonTokens.BORDER_RADIUS_MD],
  borderWidth: tokenLookup[CommonTokens.BORDER_WIDTH_THIN],
};

export type ButtonTokenBundle = ButtonTokenBlueprint;

export const getButtonTokenBundle = (): ButtonTokenBundle => ({
  background: { ...buttonTokenBlueprint.background },
  foreground: { ...buttonTokenBlueprint.foreground },
  paddingX: { ...buttonTokenBlueprint.paddingX },
  paddingY: { ...buttonTokenBlueprint.paddingY },
  borderRadius: { ...buttonTokenBlueprint.borderRadius },
  borderWidth: { ...buttonTokenBlueprint.borderWidth },
});
