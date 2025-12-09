#!/usr/bin/env python3
"""
Resolve a capability/tool name to a server using routing-profile.yaml.

Usage:
  python mcp/router-resolve.py <capability_or_tool>
Returns the server name to target.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
profile_path = ROOT / "routing-profile.yaml"
profile = yaml.safe_load(profile_path.read_text())
routes = profile.get("routes", {})
default_server = profile.get("defaults", {}).get("server")


def match(pattern: str, capability: str) -> bool:
    if pattern == "*":
        return True
    if "*" not in pattern:
        return pattern == capability
    prefix, suffix = pattern.split("*", 1)
    return capability.startswith(prefix) and capability.endswith(suffix)


def resolve(capability: str) -> str | None:
    for pattern, server in routes.items():
        if match(pattern, capability):
            return server
    return default_server


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: router-resolve.py <capability>", file=sys.stderr)
        sys.exit(1)
    cap = sys.argv[1]
    server = resolve(cap)
    if server:
        print(server)
        sys.exit(0)
    print("unresolved", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
