#!/usr/bin/env python3
"""
Auto-routing MCP proxy wrapper.

- Loads servers from mcp/mcp-suite.yaml
- Loads patterns from mcp/routing-profile.yaml
- Resolves capability -> server and calls tool

Usage:
  python mcp/router_proxy.py list-tools
  python mcp/router_proxy.py call --capability deps.drift --tool deps_trunkLint --json '{"scope":"changed"}'
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from mcp_proxy import MCPProxy
from mcp_proxy.federation import CapabilityRouter
from mcp_proxy.transports import HTTPTransport, StdioTransport

ROOT = Path(__file__).resolve().parent
SUITE_PATH = ROOT / "mcp-suite.yaml"
ROUTING_PATH = ROOT / "routing-profile.yaml"


def load_suite() -> list[dict[str, Any]]:
    data = yaml.safe_load(SUITE_PATH.read_text())
    return data.get("servers", [])


def build_router(proxy: MCPProxy) -> CapabilityRouter:
    data = yaml.safe_load(ROUTING_PATH.read_text())
    router = CapabilityRouter(proxy)
    for pattern, server in data.get("routes", {}).items():
        router.add_route(pattern, server)
    default = data.get("defaults", {}).get("server")
    if default:
        router.set_default(default)
    return router


def make_transport(cfg: dict[str, Any]):
    transport_type = cfg.get("transport", "stdio")
    name = cfg.get("name", "server")
    timeout = cfg.get("timeout", 30)

    def expand(item: str) -> str:
        return os.path.expandvars(item)

    if transport_type == "http":
        base_url = cfg.get("base_url", "")
        base_url = expand(base_url) if isinstance(base_url, str) else base_url
        headers = cfg.get("headers")
        if isinstance(headers, dict):
            headers = {
                k: expand(v) if isinstance(v, str) else v for k, v in headers.items()
            }
        return HTTPTransport(
            base_url=base_url,
            headers=headers,
            name=name,
            timeout=timeout,
        )
    cmd_raw = cfg.get("command", [])
    args_raw = cfg.get("args", [])
    command = [expand(x) if isinstance(x, str) else x for x in (cmd_raw + args_raw)]
    env = cfg.get("env")
    if isinstance(env, dict):
        env = {k: expand(v) if isinstance(v, str) else v for k, v in env.items()}
    cwd = cfg.get("cwd")
    cwd = expand(cwd) if isinstance(cwd, str) else cwd
    return StdioTransport(
        command=command,
        env=env,
        cwd=cwd,
        name=name,
        timeout=timeout,
    )


async def build_proxy() -> tuple[MCPProxy, CapabilityRouter]:
    proxy = MCPProxy()
    include_optional = os.environ.get("INCLUDE_OPTIONAL_SERVERS", "0") == "1"
    skip = {
        s.strip() for s in os.environ.get("SKIP_SERVERS", "").split(",") if s.strip()
    }
    only = {
        s.strip() for s in os.environ.get("ONLY_SERVERS", "").split(",") if s.strip()
    }
    for server in load_suite():
        if server.get("optional") and not include_optional:
            continue
        if server.get("name") in skip:
            continue
        if only and server.get("name") not in only:
            continue
        transport = make_transport(server)
        await proxy.register(server["name"], transport)
    router = build_router(proxy)
    return proxy, router


async def list_tools() -> None:
    proxy, _ = await build_proxy()
    tools = await proxy.list_tools()
    for tool in tools:
        print(tool.qualified_name)
    await proxy.close()


async def call(capability: str, tool: str, payload: dict[str, Any]) -> None:
    proxy, router = await build_proxy()
    server = router.resolve(capability)
    if not server:
        print(f"No server for capability {capability}", file=sys.stderr)
        await proxy.close()
        sys.exit(2)
    result = await proxy.call_tool(server, tool, payload)
    # result may be ToolResult or dict
    out = result.to_dict() if hasattr(result, "to_dict") else result
    print(json.dumps(out, indent=2))
    await proxy.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-routing MCP proxy")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list-tools", help="List tools across servers")
    call_p = sub.add_parser("call", help="Call a tool via routed server")
    call_p.add_argument("--capability", required=True)
    call_p.add_argument("--tool", required=True)
    call_p.add_argument("--json", default="{}", help="JSON payload")
    args = parser.parse_args()

    if args.cmd == "list-tools":
        asyncio.run(list_tools())
    else:
        try:
            payload = json.loads(args.json)
        except json.JSONDecodeError as exc:
            print(f"Invalid JSON: {exc}", file=sys.stderr)
            sys.exit(1)
        asyncio.run(call(args.capability, args.tool, payload))


if __name__ == "__main__":
    main()
