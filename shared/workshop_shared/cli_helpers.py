"""Shared Typer CLI helpers for all workshop parts."""

from __future__ import annotations

import asyncio

import typer

from workshop_shared.config import Settings, get_settings
from workshop_shared.llm.invoke_health import check_llm_invoke_health_sync
from workshop_shared.llm.ollama import check_ollama_health, is_configured_model_available
from workshop_shared.mcp.bridge import check_mcp_servers
from workshop_shared.observability.logging_trace import setup_logging
from workshop_shared.observability.otel import init_splunk_otel
from workshop_shared.slack.doctor import check_slack_health


def bootstrap_observability(settings: Settings, *, force_trace: bool = False) -> None:
    if settings.agent_log_trace or force_trace:
        setup_logging(settings)
    init_splunk_otel(settings)


def check_llm_health(settings: Settings, *, verbose: bool = False) -> None:
    if settings.llm_provider == "openai":
        if verbose:
            typer.echo("LLM provider: openai")
            typer.echo(f"Base URL: {settings.openai_base_url}")
            typer.echo(f"Model: {settings.openai_model_name}")
        ok, error = check_llm_invoke_health_sync(settings)
        if not ok:
            typer.echo(f"OpenAI-compatible LLM unreachable: {error}", err=True)
            raise typer.Exit(code=1)
        if verbose:
            typer.echo("OpenAI-compatible LLM: OK")
        return

    if settings.llm_provider == "azure_openai":
        if verbose:
            typer.echo("LLM provider: azure_openai")
        ok, error = check_llm_invoke_health_sync(settings)
        if not ok:
            typer.echo(f"Azure OpenAI unreachable: {error}", err=True)
            raise typer.Exit(code=1)
        if verbose:
            typer.echo("Azure OpenAI: OK")
        return

    if verbose:
        typer.echo("LLM provider: ollama")
    ok, models, error = check_ollama_health(settings)
    if not ok:
        typer.echo(f"Ollama unreachable: {error}", err=True)
        raise typer.Exit(code=1)
    if verbose:
        typer.echo("Ollama: OK")
    if models and not is_configured_model_available(settings, models):
        typer.echo(f"Warning: model '{settings.ollama_model}' not in tag list.", err=True)
        raise typer.Exit(code=1)


def run_mcp_doctor() -> None:
    settings = get_settings()
    if not (
        settings.enable_splunk_o11y
        or settings.enable_splunk_cloud_mcp
        or settings.enable_splunk_mcp
    ):
        typer.echo("No MCP integrations enabled.")
        raise typer.Exit(code=1)
    results = asyncio.run(check_mcp_servers(settings))
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


def run_slack_doctor() -> None:
    settings = get_settings()
    if not settings.enable_slack:
        typer.echo("Slack is not enabled. Set ENABLE_SLACK=true in .env", err=True)
        raise typer.Exit(code=1)
    ok, detail = check_slack_health(settings)
    if not ok:
        typer.echo(f"Slack check failed: {detail}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Slack: OK ({detail})")
