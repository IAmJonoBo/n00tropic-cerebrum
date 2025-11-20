import { fileURLToPath } from 'node:url';

import js from '@eslint/js';
import globals from 'globals';
import pluginImport from 'eslint-plugin-import';
import pluginN from 'eslint-plugin-n';
import pluginPromise from 'eslint-plugin-promise';
import tseslint from 'typescript-eslint';

const projectDir = fileURLToPath(new URL('.', import.meta.url));

export default tseslint.config(
  {
    ignores: ['dist', 'build', 'coverage', 'storybook-static', 'node_modules', 'public/sw.js'],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...tseslint.configs.stylistic,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.json'],
        tsconfigRootDir: projectDir,
      },
    },
  },
  {
    files: ['**/*.{js,jsx,ts,tsx}'],
    languageOptions: {
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.es2024,
      },
    },
    plugins: {
      import: pluginImport,
      n: pluginN,
      promise: pluginPromise,
    },
    settings: {
      'import/resolver': {
        typescript: {
          project: `${projectDir}/tsconfig.json`,
        },
      },
    },
    rules: {
      'import/no-unresolved': [
        'error',
        {
          ignore: ['^@n00plicate/'],
        },
      ],
      'import/newline-after-import': 'off',
      'import/order': [
        'error',
        {
          groups: ['builtin', 'external', 'internal', ['parent', 'sibling', 'index'], 'type'],
          'newlines-between': 'always',
        },
      ],
      'n/no-missing-import': 'off',
      'n/no-unsupported-features/es-syntax': 'off',
      'promise/always-return': 'off',
    },
  },
  {
    files: ['**/*.config.{js,ts}', 'vite.config.ts'],
    languageOptions: {
      globals: {
        ...globals.node,
      },
    },
  },
);
