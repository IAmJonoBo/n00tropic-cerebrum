.PHONY: help setup lint test fmt sbom

help:
	@echo "Common targets: setup lint test fmt sbom"

setup:
	@echo "Install toolchain and hooks"
	pip install pre-commit || true
	pre-commit install || true

lint:
	@echo "Run linters (language-agnostic hooks)"
	pre-commit run --all-files || true

test:
	@echo "Run project tests (delegate to language-specific tools)"

fmt:
	@echo "Format source files (delegate to language-specific tools)"

sbom:
	@echo "Generate SBOM (placeholder) -> ./security/sbom/sbom.json"
	mkdir -p security/sbom
	echo '{"bomFormat":"CycloneDX","specVersion":"1.5","version":1}' > security/sbom/sbom.json
