# Contributing to n00menon

Please follow the workspace standards:

- Use `vale` for style and `lychee` for link checks.
- Respect Antora component structure: put pages under `modules/ROOT/pages`.
- Keep topic hierarchy and add nav entries in `nav.adoc`.
- Run quick validations locally with `pnpm -C n00menon run validate` (spell + lint + verify).
- Run the full docs CI locally with `pnpm -C n00menon run docs:ci`.
- You can run spell checks explicitly using `pnpm -C n00menon run lint:spell`.
- Build the UI bundle locally with `pnpm -C n00menon run ui:build` and ensure `vendor/antora/ui-bundle.zip` is produced.

For more guidance see the workspace docs and `1. Cerebrum Docs` resources.
