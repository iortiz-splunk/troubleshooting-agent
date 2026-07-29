"""OpenTelemetry bootstrap (OTLP export to a local collector) and manual spans."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from workshop_shared.config import Settings

_logger = logging.getLogger("workshop_shared")
_otel_initialized = False


def _parse_resource_attributes(raw: str | None) -> dict[str, str]:
    """Parse OTEL_RESOURCE_ATTRIBUTES (key=value,key=value)."""
    if not raw:
        return {}
    attrs: dict[str, str] = {}
    for part in raw.split(","):
        piece = part.strip()
        if not piece or "=" not in piece:
            continue
        key, value = piece.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key:
            attrs[key] = value
    return attrs


def _otlp_http_base(endpoint: str) -> str:
    """Normalize collector base URL for OTLP/HTTP exporters."""
    base = endpoint.strip().rstrip("/")
    for suffix in ("/v1/traces", "/v1/metrics"):
        if base.endswith(suffix):
            return base[: -len(suffix)]
    return base


# ---------------------------------------------------------------------------
# OTel bootstrap
# Exports traces and metrics to a local collector over OTLP/HTTP.
# The collector handles routing to Splunk Observability Cloud or elsewhere.
# ---------------------------------------------------------------------------
def init_splunk_otel(settings: Settings) -> bool:
    """Start OTel export to the local collector (idempotent). Returns True when active."""
    global _otel_initialized
    if not settings.enable_splunk_otel or _otel_initialized:
        return _otel_initialized

    try:
        from opentelemetry import metrics, trace
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        _logger.warning(
            "ENABLE_SPLUNK_OTEL=true but OpenTelemetry packages are not installed. "
            'Run: pip install "troubleshooting-agent[observability]"'
        )
        return False

    base = _otlp_http_base(settings.otel_collector_endpoint)
    resource_attrs = {SERVICE_NAME: settings.otel_service_name}
    resource_attrs.update(_parse_resource_attributes(settings.otel_resource_attributes))
    resource = Resource.create(resource_attrs)

    span_exporter = OTLPSpanExporter(endpoint=f"{base}/v1/traces")
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    metric_exporter = OTLPMetricExporter(endpoint=f"{base}/v1/metrics")
    metric_reader = PeriodicExportingMetricReader(metric_exporter)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    _init_httpx_instrumentation()
    _otel_initialized = True
    _logger.info(
        "OTel export initialized service=%s collector=%s",
        settings.otel_service_name,
        base,
    )
    return True


# ---------------------------------------------------------------------------
# Auto-instrumentation
# httpx covers outbound LLM HTTP; LangGraph/MCP use manual spans below.
# ---------------------------------------------------------------------------
def _init_httpx_instrumentation() -> None:
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except ImportError:
        _logger.debug("opentelemetry-instrumentation-httpx not installed; LLM HTTP spans skipped")


def otel_active() -> bool:
    return _otel_initialized


# ---------------------------------------------------------------------------
# Manual span helper
# No-op when OTel is off; used for slack.alert, agent.investigation, mcp.tool, etc.
# ---------------------------------------------------------------------------
@contextmanager
def span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[Any]:
    """Manual span when OTel export is active; no-op otherwise."""
    if not _otel_initialized:
        yield None
        return

    try:
        from opentelemetry import trace
    except ImportError:
        yield None
        return

    tracer = trace.get_tracer("workshop_shared")
    with tracer.start_as_current_span(name, attributes=attributes or {}) as current:
        yield current
