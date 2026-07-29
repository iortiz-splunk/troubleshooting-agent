"""Tests for OTel bootstrap (no heavy deps required)."""

import pytest

from workshop_shared.config import Settings
from workshop_shared.observability import otel as otel_mod
from workshop_shared.observability.otel import (
    _otlp_http_base,
    _parse_resource_attributes,
    init_splunk_otel,
    span,
)


def test_init_splunk_otel_disabled() -> None:
    settings = Settings(enable_splunk_otel=False)
    assert init_splunk_otel(settings) is False


def test_parse_resource_attributes() -> None:
    assert _parse_resource_attributes("deployment.environment=demo,team=sre") == {
        "deployment.environment": "demo",
        "team": "sre",
    }


def test_otlp_http_base_strips_signal_paths() -> None:
    assert _otlp_http_base("http://localhost:4318/v1/traces") == "http://localhost:4318"


def test_init_splunk_otel_configures_otlp_exporters(monkeypatch: pytest.MonkeyPatch) -> None:
    otel_mod._otel_initialized = False
    captured: dict[str, str] = {}

    class _FakeExporter:
        def __init__(self, endpoint: str) -> None:
            captured[endpoint] = endpoint

    class _FakeProcessor:
        def __init__(self, exporter: object) -> None:
            self.exporter = exporter

    class _FakeTracerProvider:
        def __init__(self, resource: object) -> None:
            self.resource = resource
            self.processors: list[object] = []

        def add_span_processor(self, processor: object) -> None:
            self.processors.append(processor)

    class _FakeReader:
        def __init__(self, exporter: object) -> None:
            self.exporter = exporter

    monkeypatch.setattr("opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter", _FakeExporter)
    monkeypatch.setattr("opentelemetry.exporter.otlp.proto.http.metric_exporter.OTLPMetricExporter", _FakeExporter)
    monkeypatch.setattr("opentelemetry.sdk.trace.export.BatchSpanProcessor", _FakeProcessor)
    monkeypatch.setattr("opentelemetry.sdk.metrics.export.PeriodicExportingMetricReader", _FakeReader)
    monkeypatch.setattr("opentelemetry.sdk.trace.TracerProvider", _FakeTracerProvider)
    monkeypatch.setattr("opentelemetry.sdk.metrics.MeterProvider", lambda **kwargs: kwargs)
    monkeypatch.setattr("opentelemetry.trace.set_tracer_provider", lambda provider: None)
    monkeypatch.setattr("opentelemetry.metrics.set_meter_provider", lambda provider: None)
    monkeypatch.setattr(otel_mod, "_init_httpx_instrumentation", lambda: None)

    settings = Settings(
        enable_splunk_otel=True,
        otel_collector_endpoint="http://localhost:4318",
        otel_resource_attributes="deployment.environment=workshop",
    )
    assert init_splunk_otel(settings) is True
    assert "http://localhost:4318/v1/traces" in captured
    assert "http://localhost:4318/v1/metrics" in captured

    otel_mod._otel_initialized = False


def test_span_reraises_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    otel_mod._otel_initialized = True

    class _FakeSpan:
        def __enter__(self) -> "_FakeSpan":
            return self

        def __exit__(self, *args: object) -> bool:
            return False

    class _FakeTracer:
        def start_as_current_span(self, *args: object, **kwargs: object) -> _FakeSpan:
            return _FakeSpan()

    monkeypatch.setattr("opentelemetry.trace.get_tracer", lambda _name: _FakeTracer())

    with pytest.raises(RuntimeError, match="boom"):
        with span("test.span"):
            raise RuntimeError("boom")

    otel_mod._otel_initialized = False
