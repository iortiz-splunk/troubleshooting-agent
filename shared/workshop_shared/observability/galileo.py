"""Galileo Cloud callbacks for LangGraph agent traces."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from workshop_shared.config import Settings

_logger = logging.getLogger("workshop_shared")


@dataclass
class TokenUsageTotals:
    """Cumulative LLM token usage for one investigation session."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    llm_calls: int = 0

    def add(
        self,
        *,
        input_tokens: int | None,
        output_tokens: int | None,
        total_tokens: int | None,
    ) -> None:
        self.llm_calls += 1
        if input_tokens is not None:
            self.input_tokens += input_tokens
        if output_tokens is not None:
            self.output_tokens += output_tokens
        if total_tokens is not None:
            self.total_tokens += total_tokens
        elif input_tokens is not None and output_tokens is not None:
            self.total_tokens += input_tokens + output_tokens

    def to_session_metadata(self) -> dict[str, str]:
        return {
            "input_tokens": str(self.input_tokens),
            "output_tokens": str(self.output_tokens),
            "total_tokens": str(self.total_tokens),
            "llm_calls": str(self.llm_calls),
        }


@dataclass(frozen=True)
class GalileoSession:
    """LangChain callback, logger, and per-session token totals."""

    callback: Any
    logger: Any
    token_totals: TokenUsageTotals = field(default_factory=TokenUsageTotals)

# ---------------------------------------------------------------------------
# Environment wiring
# Galileo SDK reads GALILEO_* from os.environ; copy from Settings when set.
# ---------------------------------------------------------------------------
def _apply_galileo_env(settings: Settings) -> None:
    if settings.galileo_api_key:
        os.environ.setdefault("GALILEO_API_KEY", settings.galileo_api_key)
    os.environ.setdefault("GALILEO_PROJECT", settings.galileo_project)
    os.environ.setdefault("GALILEO_LOG_STREAM", settings.galileo_log_stream)
    # Required when Galileo is enabled — tenant-specific; no SDK default assumed.
    if settings.galileo_console_url:
        os.environ.setdefault("GALILEO_CONSOLE_URL", settings.galileo_console_url)


# ---------------------------------------------------------------------------
# Session naming
# Build a human-readable Galileo session name from investigation metadata.
# ---------------------------------------------------------------------------
def _normalize_workshop_part(meta: dict[str, str]) -> str | None:
    """Return part label like part2_agent from metadata."""
    part = meta.get("workshop_part", "").strip()
    if not part:
        return None
    if part.endswith("_agent"):
        return part
    return f"{part}_agent"


def build_galileo_session_name(
    investigation_id: str,
    investigation_metadata: dict[str, str] | None,
) -> str:
    """Return a session name keyed by O11y eventId plus the active workshop part."""
    meta = investigation_metadata or {}
    workshop_part = _normalize_workshop_part(meta)
    # eventId matches the alert event in O11y Cloud; fall back to incident/alert/rule.
    session_key = (
        meta.get("event_id")
        or meta.get("incident_id")
        or meta.get("alert_id")
        or meta.get("rule")
    )

    if session_key:
        parts = [f"slack-alert-{session_key}"]
        if workshop_part:
            parts.append(workshop_part)
        elif service := meta.get("service"):
            parts.append(service)
        return " | ".join(parts)

    if investigation_id.startswith("chat:"):
        base = f"chat-{investigation_id.removeprefix('chat:')}"
        if workshop_part:
            return f"{base} | {workshop_part}"
        return base
    if workshop_part:
        return f"{investigation_id} | {workshop_part}"
    return investigation_id


def _prepare_session_metadata(
    investigation_metadata: dict[str, str] | None,
) -> dict[str, str]:
    """Seed session metadata with token counters (updated on traces at flush time)."""
    metadata = dict(investigation_metadata) if investigation_metadata else {}
    for key in ("input_tokens", "output_tokens", "total_tokens", "llm_calls"):
        metadata.setdefault(key, "0")
    return metadata


def _make_token_ingestion_hook(logger: Any, totals: TokenUsageTotals):
    """Stamp cumulative token usage onto each trace, then ingest to Galileo."""

    def hook(request: Any) -> None:
        token_meta = totals.to_session_metadata()
        for trace in request.traces:
            trace.user_metadata = dict(trace.user_metadata or {})
            trace.user_metadata.update(token_meta)
        # ingestion_hook replaces the default ingest path — must forward traces.
        logger.ingest_traces(request)

    return hook


def _build_workshop_galileo_callback(
    logger: Any,
    totals: TokenUsageTotals,
) -> Any:
    from galileo.handlers.langchain import GalileoAsyncCallback
    from galileo.handlers.langchain.utils import parse_llm_result

    ingestion_hook = _make_token_ingestion_hook(logger, totals)

    class WorkshopGalileoCallback(GalileoAsyncCallback):
        async def on_llm_end(
            self,
            response: Any,
            *,
            run_id: Any,
            parent_run_id: Any | None = None,
            **kwargs: Any,
        ) -> Any:
            result = parse_llm_result(response)
            totals.add(
                input_tokens=result.num_input_tokens,
                output_tokens=result.num_output_tokens,
                total_tokens=result.total_tokens,
            )
            return await super().on_llm_end(
                response,
                run_id=run_id,
                parent_run_id=parent_run_id,
                **kwargs,
            )

    return WorkshopGalileoCallback(
        galileo_logger=logger,
        ingestion_hook=ingestion_hook,
    )


# ---------------------------------------------------------------------------
# Callback factory
# Returns GalileoAsyncCallback with a named session for each investigation.
# ---------------------------------------------------------------------------
def build_galileo_callback(
    settings: Settings,
    *,
    investigation_id: str,
    investigation_metadata: dict[str, str] | None = None,
) -> GalileoSession | None:
    """Return Galileo session (callback + logger) when Galileo is enabled."""
    if not settings.enable_galileo:
        return None
    if not settings.galileo_api_key:
        _logger.warning("ENABLE_GALILEO=true but GALILEO_API_KEY is not set")
        return None
    if not settings.galileo_console_url:
        _logger.warning("ENABLE_GALILEO=true but GALILEO_CONSOLE_URL is not set")
        return None

    _apply_galileo_env(settings)

    try:
        from galileo import GalileoLogger
    except ImportError:
        _logger.warning(
            "ENABLE_GALILEO=true but galileo is not installed. "
            'Run: pip install "troubleshooting-agent[observability]"'
        )
        return None

    session_name = build_galileo_session_name(investigation_id, investigation_metadata)
    logger = GalileoLogger(
        project=settings.galileo_project,
        log_stream=settings.galileo_log_stream,
    )
    external_id = investigation_id
    if investigation_metadata:
        external_id = (
            investigation_metadata.get("event_id")
            or investigation_metadata.get("incident_id")
            or investigation_metadata.get("alert_id")
            or investigation_id
        )
    session_metadata = _prepare_session_metadata(investigation_metadata)
    logger.start_session(
        name=session_name,
        external_id=external_id,
        metadata=session_metadata,
    )

    token_totals = TokenUsageTotals()
    callback = _build_workshop_galileo_callback(logger, token_totals)

    _logger.info(
        "Galileo session=%s project=%s stream=%s console=%s",
        session_name,
        settings.galileo_project,
        settings.galileo_log_stream,
        settings.galileo_console_url,
    )
    return GalileoSession(callback=callback, logger=logger, token_totals=token_totals)


def _workshop_part(investigation_metadata: dict[str, str] | None) -> str:
    return (investigation_metadata or {}).get("workshop_part", "")


def _emit_skill_trace(
    galileo_logger: Any,
    *,
    trace_name: str,
    trace_input: dict[str, Any],
    spans: list[dict[str, Any]],
    conclude_output: str,
    investigation_metadata: dict[str, str] | None,
    tags: list[str],
) -> None:
    try:
        galileo_logger.start_trace(
            input=json.dumps(trace_input, indent=2),
            name=trace_name,
            tags=tags,
            metadata={
                "workshop_part": _workshop_part(investigation_metadata),
                **{k: v for k, v in trace_input.items() if isinstance(v, (str, int, float, bool))},
            },
        )
        for span in spans:
            galileo_logger.add_workflow_span(**span)
        galileo_logger.conclude(output=conclude_output, status_code=200)
        galileo_logger.flush()
    except Exception:
        _logger.exception("Failed to log %s trace to Galileo", trace_name)


def _parse_skill_routing(
    investigation_metadata: dict[str, str] | None,
) -> dict[str, Any] | None:
    """Decode skill router payload from investigation metadata."""
    if not investigation_metadata:
        return None

    raw = investigation_metadata.get("skill_routing")
    if raw:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            _logger.warning("Invalid skill_routing metadata JSON")
            payload = {}
        if isinstance(payload, dict):
            return payload

    skills = [
        name.strip()
        for name in investigation_metadata.get("skills", "").split(",")
        if name.strip()
    ]
    if not skills:
        return None

    return {
        "router": investigation_metadata.get("skill_router", "keyword"),
        "domain_skill": investigation_metadata.get("skill"),
        "loaded_skills": skills,
        "scores": {},
        "chars_by_skill": {},
        "haystack_preview": "",
    }


def log_skill_router_to_galileo(
    galileo_logger: Any,
    *,
    investigation_metadata: dict[str, str] | None,
) -> None:
    """Record a pre-graph trace showing skill routing and prompt injection."""
    routing = _parse_skill_routing(investigation_metadata)
    if routing is None or galileo_logger is None:
        return

    loaded = routing.get("loaded_skills") or []
    if not loaded:
        return

    domain_skill = routing.get("domain_skill")
    scores = routing.get("scores") or {}
    chars_by_skill = routing.get("chars_by_skill") or {}
    router = routing.get("router") or "keyword"
    haystack_preview = routing.get("haystack_preview") or ""

    trace_input = {
        "router": router,
        "domain_skill": domain_skill,
        "loaded_skills": loaded,
        "scores": scores,
        "haystack_preview": haystack_preview,
    }

    try:
        spans: list[dict[str, Any]] = []
        for skill_name in loaded:
            score = scores.get(skill_name)
            chars = chars_by_skill.get(skill_name)
            if router == "graph_entry":
                role = "graph_entry"
            elif skill_name == domain_skill:
                role = "domain"
            else:
                role = "always_on"
            span_input = f"Load skill `{skill_name}` into system prompt ({role})"
            if score is not None:
                span_input += f"; keyword score={score}"

            span_output_parts: list[str] = []
            if chars is not None:
                span_output_parts.append(f"{chars} chars injected")
            span_output_parts.append("available to first LLM turn")
            spans.append(
                {
                    "input": span_input,
                    "output": "; ".join(span_output_parts),
                    "name": f"load_skill:{skill_name}",
                    "metadata": {
                        "skill": skill_name,
                        "role": role,
                        "chars_injected": chars if chars is not None else -1,
                        "keyword_score": score if score is not None else -1,
                    },
                }
            )

        _emit_skill_trace(
            galileo_logger,
            trace_name="skill_router",
            trace_input=trace_input,
            spans=spans,
            conclude_output=f"Injected {len(loaded)} skill(s): {', '.join(loaded)}",
            investigation_metadata=investigation_metadata,
            tags=["workshop", "skill_injection"],
        )
    except Exception:
        _logger.exception("Failed to log skill_router trace to Galileo")


def finalize_galileo_session_tokens(galileo_session: GalileoSession | None) -> None:
    """Record cumulative LLM token usage for the investigation in Galileo."""
    if galileo_session is None:
        return

    totals = galileo_session.token_totals
    if totals.llm_calls == 0:
        return

    token_meta = totals.to_session_metadata()
    logger = galileo_session.logger

    try:
        logger.start_trace(
            input=json.dumps({"summary": "Session token usage", **token_meta}, indent=2),
            name="session_usage",
            metadata=token_meta,
            tags=["workshop", "session_usage"],
        )
        logger.conclude(output=json.dumps(token_meta))
        logger.flush()
        _logger.info(
            "Galileo session tokens input=%s output=%s total=%s llm_calls=%s",
            totals.input_tokens,
            totals.output_tokens,
            totals.total_tokens,
            totals.llm_calls,
        )
    except Exception:
        _logger.exception("Failed to log session_usage trace to Galileo")
