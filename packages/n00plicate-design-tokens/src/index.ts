import { invariant, stableStringify } from "@n00plicate/shared-utils";

export type TokenCategory = "color" | "size" | "font" | "motion" | "misc";

export interface DesignToken<T = string> {
  name: string;
  value: T;
  description?: string;
  category?: TokenCategory;
  attributes?: Record<string, unknown>;
  deprecated?: boolean;
}

export type TokenInput<T = string> = DesignToken<T> | Record<string, T>;

export interface TokenRegistry<T = string> {
  set(token: DesignToken<T>): void;
  get(name: string): DesignToken<T> | undefined;
  remove(name: string): void;
  list(): DesignToken<T>[];
  toJSON(): Record<string, DesignToken<T>>;
}

class InMemoryRegistry<T> implements TokenRegistry<T> {
  private readonly store = new Map<string, DesignToken<T>>();

  constructor(initial?: Iterable<DesignToken<T>>) {
    if (initial) {
      for (const token of initial) {
        this.set(token);
      }
    }
  }

  set(token: DesignToken<T>) {
    invariant(token.name.trim().length > 0, "Token name is required");
    this.store.set(token.name, { ...token });
  }

  get(name: string) {
    return this.store.get(name);
  }

  remove(name: string) {
    this.store.delete(name);
  }

  list() {
    return Array.from(this.store.values()).sort((a, b) =>
      a.name.localeCompare(b.name),
    );
  }

  toJSON() {
    return Object.fromEntries(this.list().map((token) => [token.name, token]));
  }
}

export const createTokenRegistry = <T>(
  tokens?: Iterable<DesignToken<T>>,
): TokenRegistry<T> => new InMemoryRegistry(tokens);

export const normalizeTokens = <T>(input: TokenInput<T>): DesignToken<T>[] => {
  if (isDesignToken(input)) {
    return [input];
  }
  return Object.entries(input).map(([name, value]) => ({ name, value }));
};

const isDesignToken = <T>(value: TokenInput<T>): value is DesignToken<T> =>
  typeof value === "object" &&
  value !== null &&
  "name" in value &&
  "value" in value;

export const mergeTokenRegistries = <T>(
  ...registries: TokenRegistry<T>[]
): TokenRegistry<T> => {
  const merged = createTokenRegistry<T>();
  registries.forEach((registry) => {
    registry.list().forEach((token) => {
      merged.set(token);
    });
  });
  return merged;
};

export interface TokenGroup<T = string> {
  name: string;
  tokens?: DesignToken<T>[];
  groups?: TokenGroup<T>[];
}

export const flattenTokenGroups = <T>(
  group: TokenGroup<T>,
): DesignToken<T>[] => {
  const tokens = [...(group.tokens ?? [])];
  group.groups?.forEach((child) => {
    tokens.push(...flattenTokenGroups(child));
  });
  return tokens;
};

export interface TokenTheme<T = string> {
  name: string;
  description?: string;
  groups: TokenGroup<T>[];
}

export const buildThemeRegistry = <T>(
  theme: TokenTheme<T>,
): TokenRegistry<T> => {
  const registry = createTokenRegistry<T>();
  theme.groups.forEach((group) => {
    flattenTokenGroups(group).forEach((token) => {
      registry.set(token);
    });
  });
  return registry;
};

export const diffRegistries = <T>(
  baseline: TokenRegistry<T>,
  comparison: TokenRegistry<T>,
) => {
  const removed: DesignToken<T>[] = [];
  const added: DesignToken<T>[] = [];
  const changed: { token: DesignToken<T>; previous: DesignToken<T> }[] = [];

  const baselineMap = baseline.toJSON();
  const comparisonMap = comparison.toJSON();

  Object.entries(baselineMap).forEach(([name, token]) => {
    if (!(name in comparisonMap)) {
      removed.push(token);
      return;
    }
    const candidate = comparisonMap[name];
    if (stableStringify(candidate.value) !== stableStringify(token.value)) {
      changed.push({ token: candidate, previous: token });
    }
  });

  Object.entries(comparisonMap).forEach(([name, token]) => {
    if (!(name in baselineMap)) {
      added.push(token);
    }
  });

  return { added, removed, changed };
};

export const hydrateRegistry = <T>(
  registry: TokenRegistry<T>,
  ...inputs: TokenInput<T>[]
) => {
  inputs.forEach((input) => {
    normalizeTokens(input).forEach((token) => {
      registry.set(token);
    });
  });
  return registry;
};

export const registryFrom = <T>(...inputs: TokenInput<T>[]): TokenRegistry<T> =>
  hydrateRegistry(createTokenRegistry<T>(), ...inputs);

export const combineThemes = <T>(themes: TokenTheme<T>[]) =>
  themes.reduce<Record<string, TokenRegistry<T>>>((acc, theme) => {
    acc[theme.name] = buildThemeRegistry(theme);
    return acc;
  }, {});

const cloneGroup = <T>(group: TokenGroup<T>): TokenGroup<T> => ({
  name: group.name,
  tokens: group.tokens?.map((token) => ({ ...token })),
  groups: group.groups?.map(cloneGroup),
});

const mergeGroupTokens = <T>(
  current: TokenGroup<T>,
  incoming: TokenGroup<T>,
) => {
  const tokenMap = new Map<string, DesignToken<T>>();
  (current.tokens ?? []).forEach((token) => {
    tokenMap.set(token.name, token);
  });
  (incoming.tokens ?? []).forEach((token) => {
    tokenMap.set(token.name, { ...token });
  });
  current.tokens = Array.from(tokenMap.values());
};

const mergeNestedGroups = <T>(
  current: TokenGroup<T>,
  incoming: TokenGroup<T>,
) => {
  const groupMap = new Map<string, TokenGroup<T>>();
  (current.groups ?? []).forEach((group) => {
    groupMap.set(group.name, group);
  });
  (incoming.groups ?? []).forEach((group) => {
    const candidate = groupMap.get(group.name);
    if (!candidate) {
      groupMap.set(group.name, cloneGroup(group));
      return;
    }
    mergeGroupTokens(candidate, group);
    mergeNestedGroups(candidate, group);
  });
  current.groups = Array.from(groupMap.values());
};

export const mergeTokenThemes = <T>(
  base: TokenTheme<T>,
  ...extensions: TokenTheme<T>[]
): TokenTheme<T> => {
  const merged: TokenTheme<T> = {
    ...base,
    groups: base.groups.map(cloneGroup),
  };
  extensions.forEach((extension) => {
    extension.groups.forEach((incomingGroup) => {
      const existing = merged.groups.find(
        (group) => group.name === incomingGroup.name,
      );
      if (!existing) {
        merged.groups.push(cloneGroup(incomingGroup));
        return;
      }
      mergeGroupTokens(existing, incomingGroup);
      mergeNestedGroups(existing, incomingGroup);
    });
  });
  return merged;
};
