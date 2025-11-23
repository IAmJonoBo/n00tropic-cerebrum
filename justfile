# Common workspace commands (Node 24.11.1 via .nvmrc)

set shell := ['bash', '-cu']

node-check:
	./scripts/check-node-version.mjs

install: node-check
	pnpm install

dev: node-check
	pnpm dev

penpot-up: node-check
	docker compose -f n00plicate/infra/containers/devcontainer/docker-compose.yml --profile penpot-sync up -d

tokens-sync: node-check
	pnpm --filter n00plicate tokens:sync

storybook: node-check
	pnpm --filter @n00plicate/design-system run storybook

test: node-check
	pnpm -w -r test --workspace-root=false --if-present
