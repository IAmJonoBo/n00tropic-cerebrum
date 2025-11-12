.PHONY: help docs mcp-dev clean validate create-default-ui

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

docs: ## Build Antora documentation
	@echo "Building Antora documentation..."
	@pnpm -v >/dev/null 2>&1 || (corepack prepare pnpm@latest --activate)
	pnpm exec antora antora-playbook.yml --stacktrace

antora-local: ## Build Antora docs by cloning remote components into a temp dir and running a local playbook
	@bash scripts/antora-local-clone.sh

docs-ci: ## Build Antora using CI playbook (remote component sources) for CI
	@pnpm exec antora antora-playbook.ci.yml --stacktrace

convert-all: ## Run convert scripts in all known components
	@echo "Running per-repo markdown->adoc conversion scripts"
	@if [ -x n00-frontiers/scripts/convert-md-to-adoc.sh ]; then \
		bash n00-frontiers/scripts/convert-md-to-adoc.sh; \
	fi
	@if [ -x n00-cortex/scripts/convert-md-to-adoc.sh ]; then \
		bash n00-cortex/scripts/convert-md-to-adoc.sh; \
	fi
	@if [ -x n00t/scripts/convert-md-to-adoc.sh ]; then \
		bash n00t/scripts/convert-md-to-adoc.sh; \
	fi

convert-fix: ## Run convert scripts with --fix in all known components
	@echo "Running per-repo markdown->adoc conversion with --fix to auto-add headers"
	@if [ -x n00-frontiers/scripts/convert-md-to-adoc.sh ]; then \
		bash n00-frontiers/scripts/convert-md-to-adoc.sh --fix; \
	fi
	@if [ -x n00-cortex/scripts/convert-md-to-adoc.sh ]; then \
		bash n00-cortex/scripts/convert-md-to-adoc.sh --fix; \
	fi
	@if [ -x n00t/scripts/convert-md-to-adoc.sh ]; then \
		bash n00t/scripts/convert-md-to-adoc.sh --fix; \
	fi

test-ci: ## Run tests across the workspace in CI mode (non-watch)
	@echo "Running workspace tests in CI mode"
	@pnpm -w exec -- vitest run --config vitest.config.ts --reporter verbose

prepare-pnpm:
	@echo "Preparing pnpm via corepack..."
	@./scripts/setup-pnpm.sh

mcp-dev: ## Run MCP docs server locally
	@echo "Starting MCP docs server..."
	@if [ ! -f mcp/docs_server/requirements.txt ]; then \
		echo "Error: MCP server not found"; \
		exit 1; \
	fi
	@if ! python -c "import mcp" 2>/dev/null; then \
		echo "Installing MCP dependencies..."; \
		pip install -r mcp/docs_server/requirements.txt; \
	fi
	python mcp/docs_server/server.py

create-default-ui: ## Create a default Antora UI bundle under vendor/antora/ui-bundle.zip
	@echo "Creating default Antora UI bundle..."
	@bash scripts/create-default-ui-bundle.sh

validate: ## Run all validation checks
	@echo "Running Vale..."
	@if command -v vale >/dev/null 2>&1; then \
		vale docs; \
	else \
		echo "Vale not installed, skipping..."; \
	fi
	@echo "Running Lychee link checker..."
	@if command -v lychee >/dev/null 2>&1; then \
		lychee --config .lychee.toml 'docs/**/*.adoc'; \
	else \
		echo "Lychee not installed, skipping..."; \
	fi
	@echo "Checking page attributes..."
	node scripts/check-attrs.mjs

validate-docs: ## Run docs validation checks (Vale + Lychee + check-attrs). Use SKIP_VALE=1 to skip Vale locally
	@echo "Validating docs..."
	@if [ "$$SKIP_VALE" = "1" ]; then \
		echo "SKIP_VALE set - skipping Vale"; \
	else \
		echo "Running Vale..."; \
		if command -v vale >/dev/null 2>&1; then \
			vale docs; \
		else \
			echo "Vale not installed, skipping..."; \
		fi; \
	fi
	@echo "Running Lychee link checker..."
	@if command -v lychee >/dev/null 2>&1; then \
		lychee --config .lychee.toml 'docs/**/*.adoc'; \
	else \
		echo "Lychee not installed, skipping..."; \
	fi
	@echo "Checking page attributes..."
	node scripts/check-attrs.mjs

clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	rm -rf build/site
