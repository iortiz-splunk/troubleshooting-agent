"""Load workshop credentials from system env files and the login shell."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

# Facilitator-injected keys that may live in profile scripts without export.
WORKSHOP_ENV_KEYS: tuple[str, ...] = (
    "LLM_PROVIDER",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL_NAME",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_DEPLOYMENT_NAME",
    "AZURE_OPENAI_API_VERSION",
    "ENABLE_SPLUNK_O11Y",
    "SPLUNK_O11Y_GATEWAY_URL",
    "SPLUNK_O11Y_REALM",
    "SPLUNK_O11Y_API_TOKEN",
    "ENABLE_SPLUNK_CLOUD_MCP",
    "SPLUNK_CLOUD_MCP_URL",
    "SPLUNK_CLOUD_MCP_BEARER_TOKEN",
    "SPLUNK_CLOUD_MCP_TENANT",
    "ENABLE_SPLUNK_MCP",
    "SPLUNK_MCP_URL",
    "SPLUNK_MCP_BEARER_TOKEN",
    "ENABLE_SPLUNK_OTEL",
    "SPLUNK_ACCESS_TOKEN",
    "GALILEO_API_KEY",
    "GALILEO_CONSOLE_URL",
    "INSTANCE",
)

WORKSHOP_ENV_FILES: tuple[Path, ...] = (
    Path("/etc/workshop/troubleshooting-agent.env"),
    Path("/etc/workshop.env"),
    Path.home() / ".config" / "troubleshooting-agent" / "env",
)


def _load_workshop_env_files() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    for path in WORKSHOP_ENV_FILES:
        if path.is_file():
            load_dotenv(path, override=False)


def _read_vars_from_login_shell(keys: tuple[str, ...]) -> dict[str, str]:
    """Read shell variables set in profile scripts but not exported."""
    if not keys:
        return {}

    quoted_keys = " ".join(shlex.quote(key) for key in keys)
    script = f"""
set +u
[ -f /etc/profile ] && . /etc/profile >/dev/null 2>&1
[ -f "$HOME/.profile" ] && . "$HOME/.profile" >/dev/null 2>&1
[ -f "$HOME/.bashrc" ] && . "$HOME/.bashrc" >/dev/null 2>&1
for key in {quoted_keys}; do
  eval "value=\\${{key}}"
  if [ -n "${{value:-}}" ]; then
    printf '%s=%s\\n' "$key" "$value"
  fi
done
"""
    try:
        completed = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}

    if completed.returncode != 0:
        return {}

    values: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key and value:
            values[key] = value
    return values


def hydrate_workshop_env() -> None:
    """
    Merge facilitator credentials into os.environ before Settings loads.

    Workshop EC2 instances often define credentials in profile scripts as shell
    variables (visible to ``echo``) without ``export``. Child processes like
    Python only inherit exported variables, so we hydrate missing keys here.
    """
    _load_workshop_env_files()

    missing = tuple(key for key in WORKSHOP_ENV_KEYS if not os.environ.get(key))
    if not missing:
        return

    for key, value in _read_vars_from_login_shell(missing).items():
        os.environ.setdefault(key, value)
