"""Shared observability helpers for workspace entry points."""

from __future__ import annotations

import os
from typing import Any, Final, Iterable, Mapping

try:
    from opentelemetry import trace
except Exception:  # pragma: no cover - optional dependency
    trace = None

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


# -----------------------------------------------------------------------------
# Domain helpers
# -----------------------------------------------------------------------------


def _get_span():
    if trace is None:
        return None
    tracer = trace.get_tracer("n00tropic.observability")
    return tracer.start_span if tracer else None


def record_guardrail_decision(
    decision: str,
    violations: list[Mapping[str, Any]] | None = None,
    prompt_variant: str | None = None,
    workflow_id: str | None = None,
) -> None:
    """Emit a span capturing guardrail outcomes for downstream dashboards."""
    starter = _get_span()
    if starter is None:
        return
    with starter("guardrail.decision") as span:  # type: ignore[func-returns-value]
        span.set_attribute("guardrail.decision", decision)
        span.set_attribute("guardrail.violations", len(violations or []))
        if prompt_variant:
            span.set_attribute("guardrail.prompt_variant", prompt_variant)
        if workflow_id:
            span.set_attribute("workflow.id", workflow_id)


def record_routing_outcome(
    model_id: str,
    confidence: float | None = None,
    hardware_targets: Iterable[str] | None = None,
    telemetry_score: float | None = None,
) -> None:
    """Emit a span for model router selections (used in edge dashboards)."""
    starter = _get_span()
    if starter is None:
        return
    with starter("router.selection") as span:  # type: ignore[func-returns-value]
        span.set_attribute("router.model_id", model_id)
        if confidence is not None:
            span.set_attribute("router.confidence", confidence)
        if telemetry_score is not None:
            span.set_attribute("router.telemetry_score", telemetry_score)
        if hardware_targets:
            span.set_attribute("router.hardware_targets", list(hardware_targets))
