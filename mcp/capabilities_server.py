#!/usr/bin/env python3
"""Federated MCP server for n00t capability manifests."""

from __future__ import annotations

from dataclasses import dataclass
from mcp.server.fastmcp.utilities.func_metadata import ArgModelBase, FuncMetadata
from pathlib import Path
from pydantic import ConfigDict, create_model
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type

import argparse
import asyncio
import json
import logging
import mcp as mcp_package
import os
import re
import shlex
import sys
import time

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST_PATH = REPO_ROOT / "n00t" / "capabilities" / "manifest.json"
FEDERATION_MANIFEST_PATH = REPO_ROOT / "mcp" / "federation_manifest.json"

LOCAL_MCP_PATH = REPO_ROOT / "mcp"
if str(LOCAL_MCP_PATH) not in mcp_package.__path__:
    mcp_package.__path__.append(str(LOCAL_MCP_PATH))

from mcp.capabilities_manifest import (  # type: ignore[import] # noqa: E402
    Capability,
    CapabilityManifest,
)
from mcp.federation_manifest import (  # type: ignore[import] # noqa: E402
    FederatedModule,
    FederationManifest,
)

LOG_LEVEL = os.environ.get("N00T_MCP_LOG", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger("n00t.mcp.capabilities")

mcp = None  # FastMCP will be loaded lazily


@dataclass
class ModuleRuntime:
    """Runtime metadata for a module manifest."""

    id: str
    summary: str
    manifest_path: Path
    manifest_dir: Path
    workdir: Path
    manifest: CapabilityManifest
    module_meta: Optional[FederatedModule] = None


@dataclass
class RegistryConfig:
    mode: str = "federation"
    federation_path: Path = FEDERATION_MANIFEST_PATH
    module_filter: Optional[set[str]] = None
    manifest_path: Optional[Path] = None
    module_id: Optional[str] = None


class ModuleRegistry:
    """Resolves manifest modules into registered capabilities."""

    def __init__(
        self, modules: List[ModuleRuntime], federation: Optional[FederationManifest]
    ) -> None:
        if not modules:
            raise ValueError("No modules available for MCP registration.")
        self.modules = modules
        self.federation = federation
        self._assert_unique_capabilities()

    def _assert_unique_capabilities(self) -> None:
        seen: set[str] = set()
        for runtime in self.modules:
            for cap in runtime.manifest.enabled_capabilities():
                if cap.id in seen:
                    raise ValueError(
                        f"Capability id '{cap.id}' defined in multiple modules"
                    )
                seen.add(cap.id)

    @classmethod
    def from_config(cls, config: RegistryConfig, repo_root: Path) -> "ModuleRegistry":
        if config.mode == "single":
            manifest_path = config.manifest_path or DEFAULT_MANIFEST_PATH
            manifest_path = _resolve_path(manifest_path)
            module_id = config.module_id or manifest_path.stem
            runtime = cls._runtime_from_manifest(manifest_path, repo_root, module_id)
            return cls([runtime], federation=None)

        federation_path = _resolve_path(config.federation_path)
        if not federation_path.exists():
            raise FileNotFoundError(f"Federation manifest not found: {federation_path}")
        federation = FederationManifest.load(federation_path, repo_root)
        filter_ids = config.module_filter or None
        available_ids = {module.id for module in federation.modules}
        if filter_ids:
            missing = filter_ids - available_ids
            if missing:
                missing_list = ", ".join(sorted(missing))
                raise ValueError(f"Unknown module ids in filter: {missing_list}")
        modules: List[ModuleRuntime] = []
        for module in federation.modules:
            if filter_ids is not None and module.id not in filter_ids:
                continue
            if filter_ids is None and not module.includeInRoot:
                continue
            modules.append(cls._runtime_from_module(module, repo_root))
        return cls(modules, federation=federation)

    @staticmethod
    def _runtime_from_module(module: FederatedModule, repo_root: Path) -> ModuleRuntime:
        manifest_path = module.manifest_path(repo_root)
        manifest = CapabilityManifest.load(manifest_path, module.repo_path(repo_root))
        return ModuleRuntime(
            id=module.id,
            summary=module.summary,
            manifest_path=manifest_path,
            manifest_dir=manifest_path.parent,
            workdir=module.repo_path(repo_root),
            manifest=manifest,
            module_meta=module,
        )

    @staticmethod
    def _runtime_from_manifest(
        manifest_path: Path, repo_root: Path, module_id: str
    ) -> ModuleRuntime:
        manifest = CapabilityManifest.load(manifest_path, repo_root)
        summary = f"Standalone manifest {manifest_path.name}"
        return ModuleRuntime(
            id=module_id,
            summary=summary,
            manifest_path=manifest_path,
            manifest_dir=manifest_path.parent,
            workdir=repo_root,
            manifest=manifest,
            module_meta=None,
        )

    def enabled_capabilities(self) -> Iterable[Tuple[ModuleRuntime, Capability]]:
        for runtime in self.modules:
            for cap in runtime.manifest.enabled_capabilities():
                yield runtime, cap

    def module_index(self) -> List[dict[str, Any]]:
        entries: List[dict[str, Any]] = []
        for runtime in self.modules:
            all_caps = list(runtime.manifest.capabilities)
            enabled = sum(1 for cap in all_caps if cap.is_mcp_enabled())
            tags = runtime.module_meta.tags if runtime.module_meta else []
            entries.append(
                {
                    "id": runtime.id,
                    "summary": runtime.summary,
                    "manifest": _relative_to_repo(runtime.manifest_path),
                    "capabilityTotal": len(all_caps),
                    "capabilityEnabled": enabled,
                    "moduleRoot": str(runtime.workdir),
                    "tags": tags,
                }
            )
        return entries

    def health_snapshot(self) -> List[dict[str, Any]]:
        snapshot: List[dict[str, Any]] = []
        for runtime in self.modules:
            enabled_caps = list(runtime.manifest.enabled_capabilities())
            guardrails = _summarize_guardrails(enabled_caps)
            commands: List[dict[str, Any]] = []
            if runtime.module_meta:
                commands = [
                    cmd.model_dump() for cmd in runtime.module_meta.health.commands
                ]
            snapshot.append(
                {
                    "id": runtime.id,
                    "summary": runtime.summary,
                    "manifest": _relative_to_repo(runtime.manifest_path),
                    "status": "ready" if enabled_caps else "empty",
                    "capabilityEnabled": len(enabled_caps),
                    "guardrails": guardrails,
                    "healthCommands": commands,
                }
            )
        return snapshot


_registry_config = RegistryConfig()
_registry_instance: Optional[ModuleRegistry] = None


def configure_registry(config: RegistryConfig) -> None:
    global _registry_config, _registry_instance
    _registry_config = config
    _registry_instance = None


def _registry() -> ModuleRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ModuleRegistry.from_config(_registry_config, REPO_ROOT)
    return _registry_instance


class _CapabilityArgBase(ArgModelBase):
    """Base arg model that preserves optional inputs and extras."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    def model_dump_one_level(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for field_name, field_info in self.__class__.model_fields.items():
            if (
                field_name not in self.model_fields_set
                and field_info.default is not Ellipsis
            ):
                continue
            value = getattr(self, field_name)
            output_name = field_info.alias or field_name
            data[output_name] = value
        extra = getattr(self, "model_extra", None)
        if isinstance(extra, dict):
            data.update(extra)
        return data


def _sanitize_model_name(cap_id: str) -> str:
    sanitized = re.sub(r"[^0-9a-zA-Z]+", "_", cap_id).strip("_")
    return sanitized or "capability"


def _normalize_schema(schema: Dict[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(schema, dict):
        return {"type": "object"}
    normalized = dict(schema)
    normalized.setdefault("type", "object")
    return normalized


def _arg_model_for_capability(
    cap_id: str, schema: Dict[str, Any]
) -> Type[ArgModelBase]:
    properties = schema.get("properties") if isinstance(schema, dict) else None
    required = set(schema.get("required", []) if isinstance(schema, dict) else [])
    field_defs: dict[str, Any] = {}
    if isinstance(properties, dict):
        for prop_name in properties.keys():
            default = ... if prop_name in required else None
            field_defs[prop_name] = (Any, default)
    extra_behavior = "allow"
    additional = (
        schema.get("additionalProperties") if isinstance(schema, dict) else None
    )
    if isinstance(additional, bool) and additional is False:
        extra_behavior = "forbid"
    config = ConfigDict(arbitrary_types_allowed=True, extra=extra_behavior)
    model_name = f"{_sanitize_model_name(cap_id)}Inputs"
    return create_model(
        model_name,
        __base__=_CapabilityArgBase,
        __config__=config,
        **field_defs,
    )


def _func_metadata_for_capability(cap_id: str, schema: Dict[str, Any]) -> FuncMetadata:
    arg_model = _arg_model_for_capability(cap_id, schema)
    return FuncMetadata(arg_model=arg_model)


def _enabled_caps() -> list[Tuple[ModuleRuntime, Capability]]:
    return list(_registry().enabled_capabilities())


def _to_upper_snake(name: str) -> str:
    s = re.sub(r"[^0-9a-zA-Z]+", "_", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return s.upper().strip("_")


def _build_command(entrypoint: Path) -> list[str]:
    if entrypoint.suffix == ".py":
        return ["python", str(entrypoint)]
    if entrypoint.suffix == ".sh":
        return ["bash", str(entrypoint)]
    if os.access(entrypoint, os.X_OK):
        return [str(entrypoint)]
    return ["bash", str(entrypoint)]


def _register_capability(module: ModuleRuntime, cap: Capability) -> None:
    cap_id = cap.id
    inputs_schema = _normalize_schema(cap.inputs)
    entrypoint = cap.resolved_entrypoint(module.workdir, module.manifest_dir)
    summary = cap.summary
    guardrails = cap.guardrails

    async def _run(**kwargs: Any) -> Dict[str, Any]:
        cmd = _build_command(entrypoint)
        env = {k: os.environ[k] for k in guardrails.allowed_env if k in os.environ}
        env["WORKSPACE_ROOT"] = str(REPO_ROOT)
        env["CAPABILITY_ID"] = cap_id
        env["CAPABILITY_MODULE"] = module.id
        env["CAPABILITY_MANIFEST"] = _relative_to_repo(module.manifest_path)
        env["CAPABILITY_INPUTS"] = json.dumps(kwargs)
        for key, value in kwargs.items():
            env[f"INPUT_{_to_upper_snake(key)}"] = str(value)

        logger.info(
            "capability_start",
            extra={
                "capability": cap_id,
                "module": module.id,
                "command": cmd,
                "inputs": sorted(kwargs.keys()),
            },
        )

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(module.workdir),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        timed_out = False
        start = time.perf_counter()
        try:
            out_b, err_b = await asyncio.wait_for(
                proc.communicate(), timeout=guardrails.max_runtime_seconds
            )
        except asyncio.TimeoutError:
            timed_out = True
            proc.kill()
            out_b, err_b = await proc.communicate()

        out = out_b.decode(errors="replace")
        err = err_b.decode(errors="replace")
        duration = time.perf_counter() - start
        exit_code = proc.returncode
        exit_ok = exit_code in guardrails.allowed_exit_codes
        status = "ok" if (exit_ok and not timed_out) else "error"
        if timed_out:
            status = "timeout"

        payload = {
            "status": status,
            "exitCode": exit_code,
            "stdout": out[-8000:],
            "stderr": err[-8000:],
            "command": " ".join(shlex.quote(p) for p in cmd),
            "duration": round(duration, 3),
            "timedOut": timed_out,
            "module": module.id,
        }

        logger.info(
            "capability_finish",
            extra={
                "capability": cap_id,
                "module": module.id,
                "status": status,
                "exit_code": exit_code,
                "duration": payload["duration"],
                "timed_out": timed_out,
            },
        )
        return payload

    tool_name = cap_id.replace(".", "_")
    assert mcp is not None
    mcp.add_tool(_run, name=tool_name, description=summary)
    registered_tool = mcp._tool_manager.get_tool(tool_name)  # noqa: SLF001
    if registered_tool is None:
        raise RuntimeError(f"Failed to register capability '{cap_id}' as MCP tool")
    registered_tool.parameters = inputs_schema
    registered_tool.fn_metadata = _func_metadata_for_capability(cap_id, inputs_schema)


def _discover_and_register() -> None:
    global mcp
    if mcp is None:
        try:
            from mcp.server.fastmcp import FastMCP  # type: ignore
        except ImportError:
            print("fastmcp not installed. pip install mcp", file=sys.stderr)
            raise
        mcp = FastMCP("n00t-capabilities")

    for module, cap in _enabled_caps():
        _register_capability(module, cap)


def list_capabilities() -> list[str]:
    return [cap.id for _, cap in _enabled_caps()]


def list_capability_meta() -> list[Dict[str, Any]]:
    entries: list[Dict[str, Any]] = []
    for module, cap in _enabled_caps():
        entries.append(
            {
                "id": cap.id,
                "summary": cap.summary,
                "module": module.id,
                "moduleSummary": module.summary,
                "entrypoint": cap.entrypoint,
                "manifest": _relative_to_repo(module.manifest_path),
                "metadata": cap.metadata.model_dump(),
                "guardrails": cap.guardrails.model_dump(),
                "inputs": cap.inputs,
                "outputs": cap.outputs,
                "agent": cap.agent,
            }
        )
    return entries


def list_modules_metadata() -> list[Dict[str, Any]]:
    return _registry().module_index()


def list_modules_health() -> list[Dict[str, Any]]:
    return _registry().health_snapshot()


def _relative_to_repo(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _summarize_guardrails(capabilities: Iterable[Capability]) -> dict[str, Any]:
    caps = list(capabilities)
    if not caps:
        return {
            "runtimeRange": [0, 0],
            "allowedEnv": [],
            "allowedEntryRoots": [],
            "allowedExitCodes": [],
            "allowNetwork": False,
        }
    runtimes = [cap.guardrails.max_runtime_seconds for cap in caps]
    env = sorted({value for cap in caps for value in cap.guardrails.allowed_env})
    entry_roots = sorted(
        {value for cap in caps for value in cap.guardrails.allowed_entrypoint_roots}
    )
    exit_codes = sorted(
        {value for cap in caps for value in cap.guardrails.allowed_exit_codes}
    )
    allow_network = any(cap.guardrails.allow_network for cap in caps)
    return {
        "runtimeRange": [min(runtimes), max(runtimes)],
        "allowedEnv": env,
        "allowedEntryRoots": entry_roots,
        "allowedExitCodes": exit_codes,
        "allowNetwork": allow_network,
    }


def _resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else (REPO_ROOT / path).resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list",
        action="store_true",
        help="List capability IDs and exit",
    )
    parser.add_argument(
        "--list-modules",
        action="store_true",
        help="List federated modules and exit",
    )
    parser.add_argument(
        "--federation",
        type=Path,
        default=FEDERATION_MANIFEST_PATH,
        help="Path to the federation manifest",
    )
    parser.add_argument(
        "--module",
        action="append",
        dest="modules",
        help="Restrict registration to a specific module ID (repeatable)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Run a single manifest outside the federation",
    )
    parser.add_argument(
        "--module-id",
        help="Module identifier to associate with --manifest",
    )
    args = parser.parse_args()
    if args.manifest and args.modules:
        parser.error("--module cannot be combined with --manifest")
    if args.manifest:
        args.manifest = _resolve_path(args.manifest)
    args.federation = _resolve_path(args.federation)
    if args.modules:
        args.modules = sorted({module.strip() for module in args.modules if module})
    return args


def main() -> None:
    args = parse_args()
    if args.manifest:
        config = RegistryConfig(
            mode="single",
            manifest_path=args.manifest,
            module_id=args.module_id,
        )
    else:
        module_filter = set(args.modules) if args.modules else None
        config = RegistryConfig(
            mode="federation",
            federation_path=args.federation,
            module_filter=module_filter,
        )
    configure_registry(config)

    if args.list_modules:
        for module in list_modules_metadata():
            print(
                f"{module['id']}: {module['summary']} "
                f"({module['capabilityEnabled']}/{module['capabilityTotal']}) -> {module['manifest']}"
            )
        return

    if args.list:
        for name in list_capabilities():
            print(name)
        return

    _discover_and_register()
    assert mcp is not None

    @mcp.tool(
        name="n00t_capabilities_index",
        description="List MCP-enabled n00t capabilities with metadata",
    )
    def _index() -> dict[str, Any]:
        return {"capabilities": list_capability_meta()}

    @mcp.tool(
        name="n00t_capability_help", description="Describe a specific n00t capability"
    )
    def _help(capability_id: str) -> dict[str, Any]:
        for cap in list_capability_meta():
            if cap["id"] == capability_id:
                return cap
        return {"error": f"Capability '{capability_id}' not found"}

    @mcp.tool(
        name="n00t_capability_modules",
        description="List federated capability modules",
    )
    def _modules() -> dict[str, Any]:
        return {"modules": list_modules_metadata()}

    @mcp.tool(
        name="n00t_capability_health",
        description="Summarise module guardrails and readiness",
    )
    def _health() -> dict[str, Any]:
        return {"modules": list_modules_health()}

    mcp.run()


if __name__ == "__main__":
    main()
