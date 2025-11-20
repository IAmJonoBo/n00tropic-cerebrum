export type Primitive =
	| string
	| number
	| boolean
	| bigint
	| symbol
	| null
	| undefined;

export type DeepPartial<T> = T extends Primitive
	? T
	: T extends Array<infer U>
		? DeepPartial<U>[]
		: { [K in keyof T]?: DeepPartial<T[K]> };

const isPlainObject = (value: unknown): value is Record<string, unknown> =>
	Boolean(value) && Object.getPrototypeOf(value) === Object.prototype;

export const invariant = (
	condition: unknown,
	message: string,
): asserts condition => {
	if (!condition) {
		throw new Error(message);
	}
};

const mergeValue = (base: unknown, incoming: unknown): unknown => {
	if (Array.isArray(base) && Array.isArray(incoming)) {
		const clone = [...base];
		incoming.forEach((value, index) => {
			clone[index] = index in clone ? mergeValue(clone[index], value) : value;
		});
		return clone;
	}

	if (isPlainObject(base) && isPlainObject(incoming)) {
		const clone: Record<string, unknown> = {
			...(base as Record<string, unknown>),
		};
		Object.entries(incoming).forEach(([key, value]) => {
			clone[key] = key in clone ? mergeValue(clone[key], value) : value;
		});
		return clone;
	}

	return incoming ?? base;
};

export const deepMerge = <T>(target: T, ...sources: DeepPartial<T>[]): T =>
	sources.reduce<T>((acc, source) => mergeValue(acc, source) as T, target);

export type Memoized<Fn extends (...args: never[]) => unknown> = ((
	...args: Parameters<Fn>
) => ReturnType<Fn>) & {
	clear: () => void;
	size: () => number;
};

export const memoize = <Fn extends (...args: never[]) => unknown>(
	fn: Fn,
): Memoized<Fn> => {
	const cache = new Map<string, ReturnType<Fn>>();
	const memoized = ((...args: Parameters<Fn>) => {
		const key = stableStringify(args);
		const cached = cache.get(key);
		if (cached !== undefined) {
			return cached;
		}
		const result = fn(...args) as ReturnType<Fn>;
		cache.set(key, result);
		return result;
	}) as Memoized<Fn>;
	memoized.clear = () => cache.clear();
	memoized.size = () => cache.size;
	return memoized;
};

export const stableStringify = (value: unknown): string => {
	if (value === undefined) return "undefined";
	if (typeof value !== "object" || value === null) {
		return JSON.stringify(value);
	}
	if (Array.isArray(value)) {
		return `[${value.map((entry) => stableStringify(entry)).join(",")}]`;
	}
	const entries = Object.keys(value as Record<string, unknown>)
		.sort()
		.map(
			(key) =>
				`${JSON.stringify(key)}:${stableStringify((value as Record<string, unknown>)[key])}`,
		);
	return `{${entries.join(",")}}`;
};
