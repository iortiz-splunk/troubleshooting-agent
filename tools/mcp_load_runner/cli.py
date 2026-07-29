"""Headless CLI for MCP load tests (EC2 / CI)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer

from mcp_load_runner.diagnostics import configure_load_test_logging
from mcp_load_runner.metrics import records_to_csv, summary_to_json
from mcp_load_runner.preflight import run_preflight
from mcp_load_runner.runner import (
    MAX_PARTICIPANTS,
    LoadTestConfig,
    estimated_mcp_subprocesses,
    run_load_test,
)
from mcp_load_runner.scenarios import required_tool_names
from mcp_load_runner.servers import McpServerSelection
from workshop_shared.config import Settings
from workshop_shared.workshop_context import find_repo_root

app = typer.Typer(
    name="mcp-load-test",
    help="Simulate concurrent workshop MCP load (no LLM).",
    no_args_is_help=True,
)


def _env_file() -> Path:
    return find_repo_root() / ".env"


def _load_settings() -> Settings:
    env_file = _env_file()
    if env_file.is_file():
        return Settings(_env_file=str(env_file))
    return Settings()


def _print_preflight(preflight) -> None:  # type: ignore[no-untyped-def]
    typer.echo(preflight.message)
    for server in preflight.servers:
        status = "OK" if server.ok else "FAILED"
        typer.echo(f"  {server.name}: {status} ({server.tool_count} tools)")
        if server.error:
            typer.echo(f"    error: {server.error}", err=True)
        for tool_name in server.tool_names:
            typer.echo(f"    - {tool_name}")
    if preflight.missing_tools:
        typer.echo(f"  Missing: {', '.join(preflight.missing_tools)}", err=True)
    if preflight.hints:
        typer.echo("Hints:", err=not preflight.ok)
        for hint in preflight.hints:
            typer.echo(f"  - {hint}", err=not preflight.ok)
    if preflight.config_summary:
        typer.echo("Configuration (no secrets):")
        for line in preflight.config_summary:
            typer.echo(f"  {line}")


@app.command("preflight")
def preflight_command(
    servers: str = typer.Option(
        "o11y",
        "--servers",
        help="Comma-separated MCP servers to test: o11y, cloud (default: o11y).",
    ),
) -> None:
    """Check MCP connectivity and required Part 3 tools."""
    configure_load_test_logging()
    settings = _load_settings()
    env_file = _env_file()
    server_selection = McpServerSelection.from_server_names(servers)
    preflight = asyncio.run(
        run_preflight(
            settings,
            server_selection=server_selection,
            required_tools=required_tool_names(server_selection),
            env_file=str(env_file) if env_file.is_file() else None,
        )
    )
    _print_preflight(preflight)
    if not preflight.ok:
        raise typer.Exit(code=1)


@app.command("run")
def run_command(
    participants: int = typer.Option(5, "--participants", "-n", min=1, max=MAX_PARTICIPANTS),
    ramp_up: float = typer.Option(
        0.0,
        "--ramp-up",
        help="Seconds to stagger participant starts (0 = all at once).",
    ),
    service: str = typer.Option("Verification", "--service"),
    environment: str = typer.Option("Brian-E-AD-Capital", "--environment"),
    timeout: float = typer.Option(60.0, "--timeout", help="Per-tool timeout in seconds."),
    stop_on_error: bool = typer.Option(
        False,
        "--stop-on-error",
        help="Stop each participant after its first tool failure.",
    ),
    skip_preflight: bool = typer.Option(False, "--skip-preflight", help="Skip MCP preflight."),
    servers: str = typer.Option(
        "o11y",
        "--servers",
        help="Comma-separated MCP servers to load test: o11y, cloud (default: o11y).",
    ),
    output_json: Path | None = typer.Option(
        None,
        "--output-json",
        help="Write full results JSON to this path.",
    ),
    output_csv: Path | None = typer.Option(
        None,
        "--output-csv",
        help="Write per-call CSV to this path.",
    ),
) -> None:
    """Run a headless MCP load test."""
    configure_load_test_logging()
    settings = _load_settings()
    server_selection = McpServerSelection.from_server_names(servers)
    subprocess_estimate = estimated_mcp_subprocesses(
        participants,
        o11y=server_selection.use_o11y,
        cloud=server_selection.use_cloud,
    )
    typer.echo(
        f"Load test: {participants} participants, {server_selection.label}, "
        f"~{subprocess_estimate} mcp-remote processes at peak"
    )

    if not skip_preflight:
        env_file = _env_file()
        preflight = asyncio.run(
            run_preflight(
                settings,
                server_selection=server_selection,
                required_tools=required_tool_names(server_selection),
                env_file=str(env_file) if env_file.is_file() else None,
            )
        )
        _print_preflight(preflight)
        if not preflight.ok:
            raise typer.Exit(code=1)

    config = LoadTestConfig(
        participants=participants,
        ramp_up_seconds=ramp_up,
        service_name=service.strip(),
        environment_name=environment.strip(),
        call_timeout_seconds=timeout,
        stop_on_first_error=stop_on_error,
        server_selection=server_selection,
    )

    def on_progress(progress) -> None:  # type: ignore[no-untyped-def]
        typer.echo(
            f"Progress: {progress.completed}/{progress.total_participants} "
            f"(failed: {progress.failed}, in flight: {progress.in_flight})"
        )

    summary = asyncio.run(run_load_test(settings, config, on_progress=on_progress))

    typer.echo(
        f"Done — error rate {summary.error_rate_pct}%, "
        f"p95 {_fmt_ms(summary.latency_p95_ms)}, "
        f"wall clock {_fmt_ms(summary.wall_clock_ms)}"
    )
    if summary.errors_by_type:
        typer.echo(f"Errors by type: {json.dumps(summary.errors_by_type)}")

    if output_json is not None:
        output_json.write_text(summary_to_json(summary), encoding="utf-8")
        typer.echo(f"Wrote {output_json}")
    if output_csv is not None:
        output_csv.write_text(records_to_csv(summary.records), encoding="utf-8")
        typer.echo(f"Wrote {output_csv}")

    if summary.error_rate_pct > 5.0:
        raise typer.Exit(code=2)


def _fmt_ms(value: float | None) -> str:
    if value is None:
        return "n/a"
    if value >= 1000:
        return f"{value / 1000:.1f}s"
    return f"{value:.0f}ms"


def main() -> None:
    app()


if __name__ == "__main__":
    main()
