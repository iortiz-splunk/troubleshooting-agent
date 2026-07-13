"""Unified CLI — same commands in every part directory; agent varies by cwd."""

from __future__ import annotations

import typer

from workshop_shared.agent_registry import register_run_chat
from workshop_shared.cli_helpers import (
    bootstrap_observability,
    check_llm_health,
    run_mcp_doctor,
    run_slack_doctor,
)
from workshop_shared.config import get_settings
from workshop_shared.slack.listener import run_slack_listener
from workshop_shared.workshop_context import (
    PART_LABELS,
    WorkshopPartError,
    detect_workshop_part,
    load_run_chat,
)

_active_part: str | None = None

app = typer.Typer(
    name="troubleshooting-agent",
    help="AI troubleshooting agent — behavior depends on which part directory you run from.",
    no_args_is_help=True,
)


def _ensure_part_registered(*, part_override: str | None = None) -> str:
    global _active_part
    part = detect_workshop_part(override=part_override)
    if _active_part != part:
        register_run_chat(load_run_chat(part))
        _active_part = part
    return part


@app.callback()
def main(
    ctx: typer.Context,
    part: str | None = typer.Option(
        None,
        "--part",
        help="Override auto-detect: part1_agent, part2_agent, or part3_agent",
    ),
) -> None:
    """Select agent by current directory (part1_agent, part2_agent, or part3_agent)."""
    try:
        ctx.ensure_object(dict)
        ctx.obj["part"] = _ensure_part_registered(part_override=part)
    except WorkshopPartError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


def _part_label(ctx: typer.Context) -> str:
    part = (ctx.obj or {}).get("part") or _ensure_part_registered()
    return PART_LABELS.get(part, part)


@app.command()
def doctor(ctx: typer.Context) -> None:
    """Check LLM connectivity."""
    typer.echo(_part_label(ctx))
    settings = get_settings()
    try:
        check_llm_health(settings, verbose=True)
    except ValueError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Ready.")


@app.command("mcp-doctor")
def mcp_doctor(ctx: typer.Context) -> None:
    """Check Splunk MCP server connectivity."""
    typer.echo(_part_label(ctx))
    try:
        run_mcp_doctor()
    except ValueError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def chat(
    ctx: typer.Context,
    message: str = typer.Argument(..., help="Troubleshooting question or incident description"),
    trace: bool = typer.Option(False, "--trace", help="Enable brief agent/MCP trace logs"),
) -> None:
    """Send a message to the troubleshooting agent."""
    part = (ctx.obj or {}).get("part") or _ensure_part_registered()
    run_chat = load_run_chat(part)
    settings = get_settings()
    bootstrap_observability(settings, force_trace=trace)
    try:
        check_llm_health(settings)
        response = run_chat(settings, message)
    except ValueError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(f"Agent error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(response)


@app.command("slack-doctor")
def slack_doctor(ctx: typer.Context) -> None:
    """Check Slack bot token and alerts channel access."""
    typer.echo(_part_label(ctx))
    try:
        run_slack_doctor()
    except ValueError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    settings = get_settings()
    typer.echo(f"Alerts channel: #{settings.slack_alerts_channel_name}")
    typer.echo("Ready for slack-listen.")


@app.command("slack-listen")
def slack_listen(ctx: typer.Context) -> None:
    """Listen for Observability alerts in Slack and investigate in thread."""
    part = (ctx.obj or {}).get("part") or _ensure_part_registered()
    run_chat = load_run_chat(part)
    register_run_chat(run_chat)

    settings = get_settings()
    if not settings.enable_slack:
        typer.echo("Slack is not enabled. Set ENABLE_SLACK=true in .env", err=True)
        raise typer.Exit(code=1)
    try:
        check_llm_health(settings)
        run_slack_doctor()
    except ValueError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except typer.Exit:
        raise
    except Exception as exc:
        typer.echo(f"Slack check failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if not (
        settings.enable_splunk_o11y
        or settings.enable_splunk_cloud_mcp
        or settings.enable_splunk_mcp
    ):
        typer.echo(
            "Warning: no MCP integration enabled; investigations will not query live o11y data.",
            err=True,
        )

    typer.echo(_part_label(ctx))
    typer.echo(
        f"Listening on #{settings.slack_alerts_channel_name} "
        "(Ctrl+C to stop). Post an alert or send a test message."
    )
    bootstrap_observability(settings)
    try:
        run_slack_listener(settings)
    except KeyboardInterrupt:
        typer.echo("\nStopped.")
    except Exception as exc:
        typer.echo(f"Slack listener error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def main_entry() -> None:
    app()


if __name__ == "__main__":
    main_entry()
