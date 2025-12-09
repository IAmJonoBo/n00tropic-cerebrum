#!/usr/bin/env python3
"""CLI for the n00man agent foundry."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from n00man.core import AgentFoundryExecutor, AgentGovernanceError, AgentRegistry

ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = ROOT / "docs"
REGISTRY_PATH = DOCS_ROOT / "agent-registry.json"


def _load_capabilities(path: str | None) -> list[dict[str, object]]:
    if not path:
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data  # type: ignore[return-value]
    if isinstance(data, dict) and isinstance(data.get("capabilities"), list):
        return list(data["capabilities"])  # type: ignore[return-value]
    raise SystemExit("Capabilities file must be a list or include 'capabilities'.")


def _load_metadata(path: str | None) -> dict[str, object]:
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data
    raise SystemExit("Metadata file must be a JSON object.")


def scaffold_agent(args: argparse.Namespace) -> None:
    """Invoke the Agent Foundry executor with CLI parameters."""

    payload = {
        "agent_id": args.name,
        "name": args.title or args.name,
        "role": args.role,
        "description": args.description,
        "tags": args.tag or [],
        "guardrails": args.guardrail or [],
        "capabilities": _load_capabilities(args.capabilities),
        "model_config": {
            "provider": args.model_provider,
            "model": args.model_name,
            "fallbacks": args.model_fallback or [],
        },
        "owner": args.owner,
        "status": args.status,
        "metadata": _load_metadata(args.metadata),
    }

    executor = AgentFoundryExecutor(docs_root=DOCS_ROOT, registry_path=REGISTRY_PATH)
    try:
        result = asyncio.run(executor.execute(**payload))
    except AgentGovernanceError as exc:  # pragma: no cover - CLI formatting
        raise SystemExit(f"[n00man] Governance validation failed:\n{exc}") from exc

    print(f"[n00man] Scaffolded agent {result['agent_id']}")
    for generated in result["generated_files"]:
        print("  ·", generated)
    print("  registry:", result["registry_path"])


def list_agents() -> int:
    """List registered agents using the JSON registry."""
    registry = AgentRegistry(REGISTRY_PATH)
    agents = registry.list()
    if not agents:
        print(
            "[n00man] No agents registered yet. Run `n00man scaffold ...` to add one."
        )
        return 0

    for profile in agents:
        print(f"{profile.agent_id}\t{profile.status}\t{profile.role}\t{profile.name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    scaffold = subparsers.add_parser(
        "scaffold", help="Create a new agent profile using the Agent Foundry"
    )
    scaffold.add_argument("--name", required=True, help="Agent slug (kebab-case)")
    scaffold.add_argument("--role", required=True, help="Agent primary role")
    scaffold.add_argument("--title", help="Human readable agent title")
    scaffold.add_argument(
        "--description",
        required=True,
        help="Short description of the agent",
    )
    scaffold.add_argument(
        "--tag",
        action="append",
        dest="tag",
        help="Tag to add to the profile (repeatable)",
    )
    scaffold.add_argument(
        "--guardrail",
        action="append",
        dest="guardrail",
        help="Guardrail entry to add (repeatable)",
    )
    scaffold.add_argument(
        "--capabilities",
        help="Path to JSON file with capability definitions",
    )
    scaffold.add_argument(
        "--model-provider",
        default="openai",
        help="LLM provider identifier",
    )
    scaffold.add_argument(
        "--model-name",
        default="gpt-5.1-codex",
        help="Primary model name",
    )
    scaffold.add_argument(
        "--model-fallback",
        action="append",
        dest="model_fallback",
        help="Fallback model identifier (repeatable)",
    )
    scaffold.add_argument(
        "--owner",
        default="platform-ops",
        help="Owning team slug",
    )
    scaffold.add_argument(
        "--status",
        default="draft",
        choices=["draft", "beta", "active", "deprecated"],
        help="Agent lifecycle status",
    )
    scaffold.add_argument(
        "--metadata",
        help="Path to JSON file containing metadata payload",
    )

    subparsers.add_parser("list", help="List registered agents")

    args = parser.parse_args(argv)

    if args.command == "scaffold":
        scaffold_agent(args)
        return 0
    if args.command == "list":
        return list_agents()

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
