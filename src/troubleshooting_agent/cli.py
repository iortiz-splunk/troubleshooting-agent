"""Typer CLI for the troubleshooting agent."""

from __future__ import annotations

import typer

from troubleshooting_agent.agent.runner import run_chat
from troubleshooting_agent.config import get_settings
from troubleshooting_agent.llm.ollama import (
    check_ollama_health,
    is_configured_model_available,
)

app = typer.Typer(
    name="troubleshoot-agent",
    help="AI troubleshooting agent for applications and systems.",
    no_args_is_help=True,
)


@app.command()
def doctor() -> None:
    """Check Ollama connectivity and list available models."""
    settings = get_settings()
    typer.echo(f"Ollama URL: {settings.ollama_base_url}")
    typer.echo(f"Configured model: {settings.ollama_model}")

    ok, models, error = check_ollama_health(settings)
    if not ok:
        typer.echo(f"Ollama unreachable: {error}", err=True)
        raise typer.Exit(code=1)

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

    typer.echo("Ready.")


@app.command()
def chat(
    message: str = typer.Argument(..., help="Troubleshooting question or incident description"),
) -> None:
    """Send a message to the troubleshooting agent."""
    settings = get_settings()

    ok, _, error = check_ollama_health(settings)
    if not ok:
        typer.echo(f"Ollama unreachable: {error}", err=True)
        typer.echo("Start Ollama or fix OLLAMA_BASE_URL, then run: troubleshoot-agent doctor")
        raise typer.Exit(code=1)

    try:
        response = run_chat(settings, message)
    except Exception as exc:
        typer.echo(f"Agent error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(response)


def main() -> None:
    """Entry point for the console script."""
    app()


if __name__ == "__main__":
    main()
