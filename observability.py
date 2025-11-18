"""Shared observability helpers for workspace entry points."""

from __future__ import annotations

import os
from typing import Final

_DEFAULT_ENDPOINT: Final[str] = "http://127.0.0.1:4317"


def _as_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def initialize_tracing(
    service_name: str, *, default_endpoint: str | None = None
) -> bool:
    """Configure agent framework tracing when the dependency is available."""
    if _as_bool(os.environ.get("N00_DISABLE_TRACING")):
        return False

    endpoint = os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT", default_endpoint or _DEFAULT_ENDPOINT
    )
    enable_sensitive = _as_bool(os.environ.get("OTEL_ENABLE_SENSITIVE_DATA"))
    configured_service = os.environ.get("OTEL_SERVICE_NAME", service_name)

    try:
        from agent_framework.observability import setup_observability
    except Exception:
        return False

    try:
        setup_observability(
            service_name=configured_service,
            otlp_endpoint=endpoint,
            enable_sensitive_data=enable_sensitive,
        )
    except Exception:
        return False
    return True
