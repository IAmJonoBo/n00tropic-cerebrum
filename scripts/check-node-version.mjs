#!/usr/bin/env node
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const root = process.cwd();
const nvmrcPath = join(root, '.nvmrc');
const pkgPath = join(root, 'n00plicate', 'package.json');

const current = process.versions.node;
const nvmrc = existsSync(nvmrcPath) ? readFileSync(nvmrcPath, 'utf8').trim() : null;
let engine = null;
try {
  const pkg = JSON.parse(readFileSync(pkgPath, 'utf8'));
  engine = pkg.engines?.node ?? null;
} catch {}

const expected = nvmrc || engine;

if (!expected) {
    console.warn('No .nvmrc or engines.node found; skipping Node version check.');
    process.exit(0);
}

const normalize = (v) => v.replace(/^v/, '').trim();

const parse = (v) => {
    const m = normalize(v).match(/^(\d+)\.(\d+)\.(\d+)/);
    if (!m) return null;
    return { major: Number(m[1]), minor: Number(m[2]), patch: Number(m[3]) };
};

const gte = (a, b) => {
    if (a.major !== b.major) return a.major > b.major;
    if (a.minor !== b.minor) return a.minor > b.minor;
    return a.patch >= b.patch;
};

const actualSemver = parse(current);
const wantRaw = expected;
const wantIsLts = /^lts\b|^node\b/i.test(wantRaw);
const wantRange = /^>=/.test(wantRaw);

let ok = false;
let wantDisplay = wantRaw;

if (wantIsLts) {
    // For .nvmrc set to lts/* or node, use engines lower bound if available, else current LTS major
    const min = engine && engine.startsWith('>=') ? parse(engine.replace(/^>=\s*/, '')) : null;
    if (actualSemver && min) {
        ok = gte(actualSemver, min);
        wantDisplay = `>= ${min.major}.${min.minor}.${min.patch} (LTS)`;
    } else {
        ok = true; // best effort
    }
} else if (wantRange) {
    const min = parse(wantRaw.replace(/^>=\s*/, ''));
    if (actualSemver && min) {
        ok = gte(actualSemver, min);
        wantDisplay = `>= ${min.major}.${min.minor}.${min.patch}`;
    }
} else {
    const target = parse(wantRaw);
    if (actualSemver && target) {
        ok = actualSemver.major === target.major && actualSemver.minor === target.minor && actualSemver.patch === target.patch;
    }
}

if (!ok) {
    console.error(`❌ Node version mismatch: running ${current}, expected ${wantDisplay}.`);
    if (nvmrc) {
        console.error('   Try: nvm use --lts');
    }
    process.exit(1);
} else {
    console.log(`✅ Node version OK (${current}) meets ${wantDisplay}`);
}
