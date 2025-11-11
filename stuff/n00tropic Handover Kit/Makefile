.PHONY: handover check-docs

handover:
	@python3 scripts/generate_handover_packet.py

check-docs:
	@echo "Checking for required docs..."
	@test -f docs/project/HANDOVER_CONTRACT.md
	@test -f docs/project/SCOPE_CHANGE_PROTOCOL.md
	@test -f catalog-info.yaml
	@test -f contracts/openapi/OPENAPI.yaml
	@test -f contracts/asyncapi/ASYNCAPI.yaml
	@echo "Docs check passed."
