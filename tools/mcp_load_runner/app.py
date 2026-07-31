"""Streamlit UI for MCP load testing."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

import streamlit as st

from mcp_load_runner.diagnostics import configure_load_test_logging
from mcp_load_runner.metrics import (
    RunProgress,
    RunSummary,
    exemplar_trace_failure_summary,
    records_to_csv,
    slowest_tool_by_p95,
    splunk_zero_row_summary,
    suggest_next_participants,
    summary_to_json,
)
from mcp_load_runner.scenarios import (
    DEFAULT_APM_SERVICE_NAME,
    DEFAULT_ENVIRONMENT_NAME,
    DEFAULT_EXEMPLAR_TYPE,
    DEFAULT_SPLUNK_LOG_SERVICE,
    VALID_EXEMPLAR_TYPES,
)
from mcp_load_runner.preflight import run_preflight
from mcp_load_runner.runner import (
    EC2_RECOMMENDED_MIN_PARTICIPANTS,
    LAPTOP_SOFT_LIMIT,
    MAX_PARTICIPANTS,
    LoadTestConfig,
    estimated_mcp_subprocesses,
    run_load_test,
)
from mcp_load_runner.scenarios import required_tool_names
from mcp_load_runner.servers import McpServerSelection
from workshop_shared.config import Settings
from workshop_shared.workshop_context import find_repo_root

_REPO_ROOT = find_repo_root()
_ENV_FILE = _REPO_ROOT / ".env"
_PAGE_BOTTOM_PADDING = "8rem"


def _inject_page_styles() -> None:
    """Extra bottom padding so downloads and charts are not clipped when scrolling."""
    st.markdown(
        f"""
        <style>
        section.main .block-container {{
            padding-bottom: {_PAGE_BOTTOM_PADDING};
        }}
        div[data-testid="stSidebar"] .block-container {{
            padding-bottom: 2rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _page_bottom_spacer() -> None:
    st.markdown(f"<div aria-hidden='true' style='height:{_PAGE_BOTTOM_PADDING};'></div>", unsafe_allow_html=True)


def _load_settings() -> Settings:
    if _ENV_FILE.is_file():
        return Settings(_env_file=str(_ENV_FILE))
    return Settings()


def _run_async(coro):  # type: ignore[no-untyped-def]
    """Run async code from Streamlit (which may already have an event loop)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()


def _participant_warnings(selection: McpServerSelection, participants: int) -> None:
    subprocesses = estimated_mcp_subprocesses(
        participants,
        o11y=selection.use_o11y,
        cloud=selection.use_cloud,
    )
    st.caption(
        f"Peak ~{subprocesses} mcp-remote subprocesses ({participants} participants, "
        f"{selection.label})."
    )
    if participants <= LAPTOP_SOFT_LIMIT:
        return
    if participants <= 50:
        st.warning(
            f"Above {LAPTOP_SOFT_LIMIT} participants is not recommended on a laptop. "
            "Use a dedicated EC2 runner."
        )
    elif participants < EC2_RECOMMENDED_MIN_PARTICIPANTS:
        st.info("Medium load — an r7i.2xlarge (64 GB) EC2 instance is usually sufficient.")
    elif participants <= 100:
        st.warning(
            "High load — use r7i.4xlarge (128 GB RAM) or larger. "
            "Run `ulimit -n 65535` before starting."
        )
    else:
        st.error(
            f"Stress test ({participants} participants) — use r7i.4xlarge or r7i.8xlarge, "
            "pre-warm mcp-remote, and prefer headless: "
            "`mcp-load-test run -n {participants} --output-json results.json`"
        )


def main() -> None:
    log_handler = configure_load_test_logging()
    st.set_page_config(
        page_title="MCP Load Test — AI SRE Agent Workshop",
        page_icon="📊",
        layout="wide",
    )
    _inject_page_styles()
    st.title("MCP Load Test Tool")
    st.caption(
        "Simulate concurrent Part 3 APM workshop participants against Splunk MCP servers "
        "(no LLM — scripted tool calls only). Supports up to "
        f"{MAX_PARTICIPANTS} participants on a dedicated runner."
    )

    settings = _load_settings()

    with st.sidebar:
        st.header("Configuration")
        st.subheader("MCP servers")
        use_o11y = st.checkbox(
            "Splunk O11y Cloud (APM)",
            value=True,
            help="Alerts, APM services, latency, and errors. Exemplar traces are optional.",
        )
        use_cloud = st.checkbox(
            "Splunk Cloud (logs)",
            value=False,
            help="splunk_run_query against workshop log index.",
        )
        include_exemplar_traces = st.checkbox(
            "Include exemplar traces",
            value=False,
            help=(
                "Adds o11y_get_apm_exemplar_traces (SignalFx GraphQL). Often returns 503 under "
                "concurrent load — leave off for capacity tests; enable for 1-participant smoke tests."
            ),
            disabled=not use_o11y,
        )
        exemplar_type = DEFAULT_EXEMPLAR_TYPE
        if include_exemplar_traces and use_o11y:
            exemplar_type = st.selectbox(
                "Exemplar type",
                options=list(VALID_EXEMPLAR_TYPES),
                index=list(VALID_EXEMPLAR_TYPES).index(DEFAULT_EXEMPLAR_TYPE),
                help="err for error alerts; lat_buck_ for latency alerts (trailing underscore).",
            )
        server_selection: McpServerSelection | None = None
        if not use_o11y and not use_cloud:
            st.error("Select at least one MCP server.")
        else:
            server_selection = McpServerSelection(use_o11y=use_o11y, use_cloud=use_cloud)
            st.caption(
                f"Scenario: {len(required_tool_names(server_selection, include_exemplar_traces=include_exemplar_traces))} "
                "tool call(s) per participant."
            )

        participants = st.slider(
            "Participants",
            min_value=1,
            max_value=MAX_PARTICIPANTS,
            value=5,
        )
        if server_selection is not None:
            _participant_warnings(server_selection, participants)
        ramp_up = st.slider(
            "Ramp-up (seconds)",
            min_value=0,
            max_value=300,
            value=0,
            help="0 = all participants start at once. Use 60–120s for large EC2 runs.",
        )
        service_name = st.text_input(
            "APM service name (O11y)",
            value=DEFAULT_APM_SERVICE_NAME,
            help="Service name passed to o11y_* MCP tools (alerts, latency, exemplar traces).",
        )
        splunk_log_service = st.text_input(
            "Splunk log search term",
            value=DEFAULT_SPLUNK_LOG_SERVICE,
            help="Token for Splunk _raw search only (splunk_run_query step).",
        )
        environment_name = st.text_input(
            "APM environment",
            value=DEFAULT_ENVIRONMENT_NAME,
        )
        call_timeout = st.number_input(
            "Per-call timeout (seconds)",
            min_value=10,
            max_value=300,
            value=60,
        )
        stop_on_first_error = st.checkbox("Stop each participant on first tool error", value=False)

        st.divider()
        preflight_disabled = server_selection is None
        if st.button(
            "Run MCP preflight",
            width="stretch",
            disabled=preflight_disabled,
        ):
            log_handler.lines.clear()
            with st.spinner("Checking MCP servers..."):
                preflight = _run_async(
                    run_preflight(
                        settings,
                        server_selection=server_selection,
                        required_tools=required_tool_names(
                            server_selection,
                            include_exemplar_traces=include_exemplar_traces,
                        ),
                        env_file=str(_ENV_FILE) if _ENV_FILE.is_file() else None,
                    )
                )
            st.session_state["preflight"] = preflight
            st.session_state["preflight_logs"] = list(log_handler.lines)
            st.session_state["preflight_server_selection"] = server_selection
            st.session_state["preflight_include_exemplar"] = include_exemplar_traces

    preflight = st.session_state.get("preflight")
    preflight_selection = st.session_state.get("preflight_server_selection")
    preflight_include_exemplar = st.session_state.get("preflight_include_exemplar")
    st.subheader("Confirm MCP Servers Are Ready")
    if server_selection is not None and preflight_selection != server_selection:
        st.warning("MCP server selection changed — re-run preflight before starting a load test.")
    if preflight is not None and preflight_include_exemplar != include_exemplar_traces:
        st.warning("Exemplar trace setting changed — re-run preflight before starting a load test.")
    if preflight is None:
        st.info("Run **MCP preflight** in the sidebar before starting a load test.")
    else:
        if preflight.ok:
            st.success(preflight.message)
        else:
            st.error(preflight.message)
        for server in preflight.servers:
            status = "OK" if server.ok else "FAIL"
            if server.ok and server.tool_count == 0:
                status = "WARN (0 tools)"
            st.write(f"**{server.name}** — {status} ({server.tool_count} tools)")
            if server.tool_names:
                with st.expander(f"Tools on {server.name}", expanded=server.tool_count == 0):
                    for tool_name in server.tool_names:
                        st.code(tool_name, language=None)
            elif server.ok:
                st.caption("No tools returned from list_tools().")
            if server.error:
                st.caption(server.error)
        if preflight.missing_tools:
            st.warning("Missing tools: " + ", ".join(preflight.missing_tools))
        if preflight.hints:
            st.markdown("**What to check**")
            for hint in preflight.hints:
                st.markdown(f"- {hint}")
        if preflight.config_summary:
            with st.expander("Configuration (no secrets)", expanded=not preflight.ok):
                st.code("\n".join(preflight.config_summary), language="ini")
        preflight_logs = st.session_state.get("preflight_logs")
        if preflight_logs:
            with st.expander("Diagnostic log", expanded=not preflight.ok):
                st.code("\n".join(preflight_logs), language="log")

    preflight_ok = (
        preflight is not None
        and preflight.ok
        and server_selection is not None
        and preflight_selection == server_selection
        and preflight_include_exemplar == include_exemplar_traces
    )
    run_disabled = not preflight_ok or server_selection is None

    st.divider()
    st.subheader("Run Load Test")

    config = LoadTestConfig(
        participants=participants,
        ramp_up_seconds=float(ramp_up),
        service_name=service_name.strip(),
        splunk_log_service=splunk_log_service.strip(),
        environment_name=environment_name.strip(),
        call_timeout_seconds=float(call_timeout),
        stop_on_first_error=stop_on_first_error,
        include_exemplar_traces=include_exemplar_traces,
        exemplar_type=str(exemplar_type),
        server_selection=server_selection or McpServerSelection(),
    )

    col_run, col_smoke = st.columns(2)
    with col_smoke:
        if st.button("Dry run (1 participant)", disabled=run_disabled):
            smoke_config = LoadTestConfig(
                participants=1,
                ramp_up_seconds=0.0,
                service_name=service_name.strip(),
                splunk_log_service=splunk_log_service.strip(),
                environment_name=environment_name.strip(),
                call_timeout_seconds=float(call_timeout),
                stop_on_first_error=stop_on_first_error,
                include_exemplar_traces=include_exemplar_traces,
                exemplar_type=str(exemplar_type),
                server_selection=config.server_selection,
            )
            _execute_load_test(settings, smoke_config)

    with col_run:
        if st.button(
            f"Start load test ({participants} participants)",
            type="primary",
            disabled=run_disabled,
        ):
            _execute_load_test(settings, config)

    if participants > LAPTOP_SOFT_LIMIT:
        st.info(
            "For large runs on EC2, prefer the headless CLI:\n\n"
            f"`mcp-load-test run -n {participants} --servers o11y --ramp-up {int(ramp_up)} "
            "--output-json results.json`"
        )

    summary: RunSummary | None = st.session_state.get("last_summary")
    if summary is not None:
        _render_results(summary)

    _page_bottom_spacer()


def _execute_load_test(settings: Settings, config: LoadTestConfig) -> None:
    log_handler = configure_load_test_logging()
    log_handler.lines.clear()
    progress_placeholder = st.empty()
    progress_state = RunProgress(total_participants=config.participants)

    def on_progress(progress: RunProgress) -> None:
        progress_state.completed = progress.completed
        progress_state.failed = progress.failed
        progress_state.in_flight = progress.in_flight
        progress_placeholder.progress(
            progress.completed / max(progress.total_participants, 1),
            text=(
                f"Completed {progress.completed}/{progress.total_participants} "
                f"(in flight: {progress.in_flight}, failed: {progress.failed})"
            ),
        )

    with st.spinner("Running load test..."):
        summary = _run_async(
            run_load_test(settings, config, on_progress=on_progress)
        )
    st.session_state["last_summary"] = summary
    st.session_state["run_logs"] = list(log_handler.lines)
    progress_placeholder.empty()
    st.rerun()


def _render_run_config(summary: RunSummary) -> None:
    config = summary.run_config
    if config is None:
        return
    ramp_label = f"{config.ramp_up_seconds:g}s" if config.ramp_up_seconds else "none (all at once)"
    st.markdown("**Run configuration**")
    st.caption(
        f"{config.server_selection_label} · "
        f"O11y service `{config.service_name}` · Splunk log `{config.splunk_log_service}` · "
        f"environment `{config.environment_name}` · "
        f"exemplar traces {'on' if config.include_exemplar_traces else 'off'}"
        f"{f' ({config.exemplar_type})' if config.include_exemplar_traces else ''} · "
        f"{config.steps_per_participant} tool call(s)/participant · "
        f"ramp-up {ramp_label} · timeout {config.call_timeout_seconds:g}s"
    )
    if config.finished_at:
        st.caption(f"Finished at {config.finished_at}")


def _render_results(summary: RunSummary) -> None:
    st.divider()
    st.subheader("Review Load Test Results")
    _render_run_config(summary)

    slowest_tool = slowest_tool_by_p95(summary.latency_by_tool)
    if slowest_tool is not None:
        tool_name, p95_ms = slowest_tool
        st.info(f"Slowest tool: `{tool_name}` (p95 {_fmt_ms(p95_ms)})")

    splunk_warning = splunk_zero_row_summary(summary.records)
    if splunk_warning:
        st.warning(splunk_warning)

    exemplar_warning = exemplar_trace_failure_summary(summary.records)
    if exemplar_warning:
        st.warning(exemplar_warning)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Participants", summary.participants)
    c2.metric("Error rate", f"{summary.error_rate_pct}%")
    c3.metric("p95 latency", _fmt_ms(summary.latency_p95_ms))
    c4.metric("Wall clock", _fmt_ms(summary.wall_clock_ms))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Total calls", summary.total_calls)
    c6.metric("Failed calls", summary.failed_calls)
    c7.metric("Calls/sec", summary.calls_per_second)
    c8.metric("Slowest participant", summary.slowest_participant_id or "—")
    if summary.slowest_participant_ms is not None:
        st.caption(f"Slowest participant wall time: {_fmt_ms(summary.slowest_participant_ms)}")

    if summary.first_failure_at:
        st.caption(f"First failure at: {summary.first_failure_at}")

    if summary.errors_by_type:
        st.write("**Errors by type**")
        st.json(summary.errors_by_type)

    if summary.latency_by_tool:
        st.write("**Latency by tool (p95 ms)**")
        tool_rows = sorted(
            [
                {
                    "tool": tool_name,
                    "p50_ms": round(stats.get("p50_ms") or 0, 1),
                    "p95_ms": round(stats.get("p95_ms") or 0, 1),
                    "p99_ms": round(stats.get("p99_ms") or 0, 1),
                    "count": int(stats.get("count") or 0),
                }
                for tool_name, stats in summary.latency_by_tool.items()
            ],
            key=lambda row: row["p95_ms"],
            reverse=True,
        )
        st.dataframe(tool_rows, width="stretch", hide_index=True)

    failures = [record for record in summary.records if not record.success]
    if failures:
        st.write("**Failed tool calls**")
        st.dataframe(
            [
                {
                    "participant": record.participant_id,
                    "step": record.step,
                    "tool": record.tool_name,
                    "server": record.server,
                    "error_type": record.error_type,
                    "error": record.error_message,
                }
                for record in failures
            ],
            width="stretch",
            hide_index=True,
        )

    if summary.records:
        durations = sorted(
            [
                {
                    "participant": record.participant_id,
                    "step": record.step,
                    "tool": record.tool_name,
                    "duration_ms": round(record.duration_ms, 1),
                }
                for record in summary.records
                if record.success
            ],
            key=lambda row: (row["participant"], row["step"]),
        )
        if durations:
            st.write("**Call duration by participant and step**")
            st.bar_chart(durations, x="tool", y="duration_ms", color="participant")

    run_logs = st.session_state.get("run_logs")
    if run_logs:
        with st.expander("Run diagnostic log", expanded=summary.failed_calls > 0):
            st.code("\n".join(run_logs), language="log")

    download_col_json, download_col_csv = st.columns(2)
    with download_col_json:
        st.download_button(
            "Download results.json",
            data=summary_to_json(summary),
            file_name="mcp_load_test_results.json",
            mime="application/json",
            width="stretch",
        )
    with download_col_csv:
        st.download_button(
            "Download results.csv",
            data=records_to_csv(summary.records),
            file_name="mcp_load_test_results.csv",
            mime="text/csv",
            width="stretch",
        )

    config = summary.run_config
    use_o11y = config.use_o11y if config else True
    use_cloud = config.use_cloud if config else False

    if summary.error_rate_pct > 5.0 or (summary.latency_p95_ms or 0) > 30_000:
        st.warning(
            "Capacity threshold exceeded: error rate > 5% or p95 latency > 30s. "
            "Reduce workshop seat count or investigate MCP gateway limits."
        )
    elif summary.error_rate_pct == 0.0:
        st.success(suggest_next_participants(
            participants=summary.participants,
            error_rate_pct=summary.error_rate_pct,
            use_o11y=use_o11y,
            use_cloud=use_cloud,
        ))


def _fmt_ms(value: float | None) -> str:
    if value is None:
        return "—"
    if value >= 1000:
        return f"{value / 1000:.1f}s"
    return f"{value:.0f}ms"


if __name__ == "__main__":
    main()
