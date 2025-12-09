#!/usr/bin/env python3
"""
Small helper to demonstrate CapabilityRouter usage with mcp-proxy.
Loads routing-profile.yaml and prints resolved server for sample capabilities.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
profile = yaml.safe_load((ROOT / "routing-profile.yaml").read_text())

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
    samples = [
        "docs.index",
        "deps.sbom",
        "fusion.pipeline",
        "workspace.gitDoctor",
        "unknown.cap",
    ]
    for cap in samples:
        print(f"{cap} -> {resolve(cap)}")


if __name__ == "__main__":
    main()
