"""Typer CLI for the troubleshooting agent."""

from __future__ import annotations

import asyncio

import typer

from troubleshooting_agent.agent.runner import run_chat
from troubleshooting_agent.config import Settings, get_settings
from troubleshooting_agent.llm.invoke_health import check_llm_invoke_health_sync
from troubleshooting_agent.llm.ollama import (
    check_ollama_health,
    is_configured_model_available,
)
from troubleshooting_agent.mcp.bridge import check_mcp_servers
from troubleshooting_agent.observability.logging_trace import setup_logging
from troubleshooting_agent.observability.otel import init_splunk_otel
from troubleshooting_agent.slack.doctor import check_slack_health
from troubleshooting_agent.slack.listener import run_slack_listener

app = typer.Typer(
    name="troubleshoot-agent",
    help="AI troubleshooting agent for applications and systems.",
    no_args_is_help=True,
)


def _bootstrap_observability(settings: Settings, *, force_trace: bool = False) -> None:
    """Initialize logging trace and Splunk OTel when enabled."""
    if settings.agent_log_trace or force_trace:
        setup_logging(settings)
    init_splunk_otel(settings)


def _check_llm_health(settings: Settings, *, verbose: bool = False) -> None:
    """Exit with code 1 if the configured LLM provider is unreachable."""
    if settings.llm_provider == "openai":
        if verbose:
            typer.echo("LLM provider: openai")
            typer.echo(f"Base URL: {settings.openai_base_url}")
            typer.echo(f"Model: {settings.openai_model_name}")
        ok, error = check_llm_invoke_health_sync(settings)
        if not ok:
            typer.echo(f"OpenAI-compatible LLM unreachable: {error}", err=True)
            typer.echo(
                "Check OPENAI_API_KEY and OPENAI_BASE_URL in .env, "
                "then run: troubleshoot-agent doctor",
                err=True,
            )
            raise typer.Exit(code=1)
        if verbose:
            typer.echo("OpenAI-compatible LLM: OK")
        return

    if settings.llm_provider == "azure_openai":
        if verbose:
            typer.echo("LLM provider: azure_openai")
            typer.echo(f"Endpoint: {settings.azure_openai_endpoint}")
            typer.echo(f"Deployment: {settings.azure_openai_deployment_name}")
        ok, error = check_llm_invoke_health_sync(settings)
        if not ok:
            typer.echo(f"Azure OpenAI unreachable: {error}", err=True)
            typer.echo(
                "Check AZURE_OPENAI_* variables in .env, then run: troubleshoot-agent doctor",
                err=True,
            )
            raise typer.Exit(code=1)
        if verbose:
            typer.echo("Azure OpenAI: OK")
        return

    if verbose:
        typer.echo("LLM provider: ollama")
        typer.echo(f"Ollama URL: {settings.ollama_base_url}")
        typer.echo(f"Configured model: {settings.ollama_model}")
    ok, models, error = check_ollama_health(settings)
    if not ok:
        typer.echo(f"Ollama unreachable: {error}", err=True)
        typer.echo("Start Ollama or fix OLLAMA_BASE_URL, then run: troubleshoot-agent doctor")
        raise typer.Exit(code=1)
    if verbose:
        typer.echo("Ollama: OK")
        if models:
            typer.echo("Available models:")
            for name in models:
                typer.echo(f"  - {name}")
        else:
            typer.echo("No models found. Run: ollama pull <model>")
    if models and not is_configured_model_available(settings, models):
        typer.echo(
            f"Warning: configured model '{settings.ollama_model}' not in tag list.",
            err=True,
        )
        raise typer.Exit(code=1)


@app.command()
def doctor() -> None:
    """Check LLM connectivity (Ollama, OpenAI-compatible, or Azure OpenAI)."""
    settings = get_settings()
    try:
        _check_llm_health(settings, verbose=True)
    except ValueError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Ready.")


@app.command("mcp-doctor")
def mcp_doctor() -> None:
    """Check Splunk MCP server connectivity and list available tools."""
    settings = get_settings()

    if not (
        settings.enable_splunk_o11y
        or settings.enable_splunk_cloud_mcp
        or settings.enable_splunk_mcp
    ):
        typer.echo("No MCP integrations enabled.")
        typer.echo(
            "Set ENABLE_SPLUNK_O11Y, ENABLE_SPLUNK_CLOUD_MCP, and/or ENABLE_SPLUNK_MCP in .env"
        )
        raise typer.Exit(code=1)

    try:
        results = asyncio.run(check_mcp_servers(settings))
    except ValueError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(f"MCP check failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    exit_code = 0
    for info in results:
        if info.ok:
            typer.echo(f"{info.name}: OK ({info.tool_count} tools)")
            for name in info.tool_names:
                typer.echo(f"  - {name}")
        else:
            typer.echo(f"{info.name}: FAILED — {info.error}", err=True)
            exit_code = 1

    if exit_code:
        raise typer.Exit(code=exit_code)
    typer.echo("MCP ready.")


@app.command()
def chat(
    message: str = typer.Argument(..., help="Troubleshooting question or incident description"),
    trace: bool = typer.Option(
        False,
        "--trace",
        help="Enable brief agent/MCP trace logs for this run",
    ),
) -> None:
    """Send a message to the troubleshooting agent."""
    settings = get_settings()
    _bootstrap_observability(settings, force_trace=trace)

    try:
        _check_llm_health(settings, verbose=False)
    except ValueError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    try:
        response = run_chat(settings, message)
    except ValueError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(f"Agent error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(response)


@app.command("slack-doctor")
def slack_doctor() -> None:
    """Check Slack bot token and alerts channel access."""
    settings = get_settings()
    if not settings.enable_slack:
        typer.echo("Slack is not enabled. Set ENABLE_SLACK=true in .env", err=True)
        raise typer.Exit(code=1)
    try:
        ok, detail = check_slack_health(settings)
    except ValueError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if not ok:
        typer.echo(f"Slack check failed: {detail}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Slack: OK ({detail})")
    typer.echo(f"Alerts channel: #{settings.slack_alerts_channel_name}")
    typer.echo("Ready for slack-listen.")


@app.command("slack-listen")
def slack_listen() -> None:
    """Listen for Observability alerts in Slack and investigate in thread (demo)."""
    settings = get_settings()
    if not settings.enable_slack:
        typer.echo("Slack is not enabled. Set ENABLE_SLACK=true in .env", err=True)
        raise typer.Exit(code=1)

    try:
        _check_llm_health(settings, verbose=False)
        ok, detail = check_slack_health(settings)
        if not ok:
            typer.echo(f"Slack check failed: {detail}", err=True)
            raise typer.Exit(code=1)
    except ValueError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
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

    typer.echo(
        f"Listening on #{settings.slack_alerts_channel_name} "
        "(Ctrl+C to stop). Post an alert or send a test message."
    )
    _bootstrap_observability(settings)
    try:
        run_slack_listener(settings)
    except KeyboardInterrupt:
        typer.echo("\nStopped.")
    except Exception as exc:
        typer.echo(f"Slack listener error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def main() -> None:
    """Entry point for the console script."""
    app()


if __name__ == "__main__":
    main()
