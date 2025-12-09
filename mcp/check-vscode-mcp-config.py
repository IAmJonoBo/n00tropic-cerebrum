#!/usr/bin/env python3
"""Validate VS Code MCP config entries for local python servers."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable

DEFAULT_CONFIG = (
    Path.home() / "Library" / "Application Support" / "Code" / "User" / "mcp.json"
)


def _strip_jsonc(raw: str) -> str:
    """Remove // and /* */ comments so json.loads can parse the file."""

    no_block = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
    return re.sub(r"//.*", "", no_block)


def load_config(path: Path) -> Dict[str, Any]:
    text = path.read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(_strip_jsonc(text))


def validate_server(
    name: str,
    server: Dict[str, Any],
    workspace_root: Path,
) -> Iterable[str]:
    if server.get("type") != "stdio":
        return []

    errors: list[str] = []
    cmd = server.get("command", "")
    if not cmd:
        errors.append(f"[{name}] missing command")
    else:
        cmd_path = Path(os.path.expandvars(cmd)).expanduser()
        if not cmd_path.exists():
            errors.append(f"[{name}] command not found: {cmd_path}")

    args = server.get("args", [])
    if not isinstance(args, list) or not args:
        errors.append(f"[{name}] missing args")
    else:
        target = Path(args[0]).expanduser()
        if not target.exists():
            errors.append(f"[{name}] target script not found: {target}")

    env = server.get("env", {})
    expected_root = str(workspace_root)
    if env.get("WORKSPACE_ROOT") != expected_root:
        errors.append(
            f"[{name}] WORKSPACE_ROOT mismatch (expected {expected_root}, got {env.get('WORKSPACE_ROOT')!r})"
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Path to VS Code MCP config (defaults to user settings)",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Root of the n00tropic-cerebrum workspace",
    )

    args = parser.parse_args()

    if not args.config.exists():
        print(f"Config file not found: {args.config}", file=sys.stderr)
        return 1

    cfg = load_config(args.config)
    servers = cfg.get("servers", {})
    failures: list[str] = []

    for name in ("docs", "n00t-capabilities"):
        server = servers.get(name)
        if not server:
            failures.append(f"[{name}] server missing from config")
            continue
        failures.extend(validate_server(name, server, args.workspace_root))

    if failures:
        print("Found configuration issues:\n - " + "\n - ".join(failures))
        return 2

    print("VS Code MCP config looks good for docs + n00t-capabilities servers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
