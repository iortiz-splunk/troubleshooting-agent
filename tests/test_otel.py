"""Tests for Splunk OTel bootstrap (no heavy deps required)."""

import pytest

from workshop_shared.config import Settings
from workshop_shared.observability import otel as otel_mod
from workshop_shared.observability.otel import init_splunk_otel, span


def test_init_splunk_otel_disabled() -> None:
    settings = Settings(enable_splunk_otel=False)
    assert init_splunk_otel(settings) is False


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
