.PHONY: help docs mcp-dev clean validate

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

docs: ## Build Antora documentation
	@echo "Building Antora documentation..."
	npx antora antora-playbook.yml --stacktrace

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

clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	rm -rf build/site
