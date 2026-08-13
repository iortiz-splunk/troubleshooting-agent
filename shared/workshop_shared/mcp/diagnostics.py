"""Diagnostics helpers for mcp-doctor — safe context without secrets."""

from __future__ import annotations

import asyncio
import os
import ssl
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp import StdioServerParameters

    from workshop_shared.config import Settings


def extract_mcp_remote_url(args: list[str]) -> str | None:
    """Return the MCP server URL from an mcp-remote argv list."""
    try:
        index = args.index("mcp-remote")
    except ValueError:
        return None
    for arg in args[index + 1 :]:
        if not arg.startswith("-"):
            return arg
    return None


def _redact_header_arg(header: str) -> str:
    if ":" not in header:
        return header
    name, _, value = header.partition(":")
    name = name.strip()
    value = value.strip()
    if not value:
        return header
    if name.lower() in {"authorization", "x-sf-token"} or value.lower().startswith("bearer "):
        return f"{name}: *** ({len(value)} chars)"
    return header


def format_mcp_remote_command(params: StdioServerParameters) -> str:
    """Format mcp-remote command with auth header values redacted."""
    parts: list[str] = [params.command]
    skip_header_value = False
    for arg in params.args:
        if skip_header_value:
            parts.append(_redact_header_arg(arg))
            skip_header_value = False
            continue
        if arg == "--header":
            parts.append(arg)
            skip_header_value = True
            continue
        parts.append(arg)
    return " ".join(parts)


def _credential_status(value: str | None) -> str:
    if not value or not str(value).strip():
        return "missing"
    return f"set ({len(str(value).strip())} chars)"


def _tls_summary(settings: Settings) -> str:
    parts: list[str] = []
    if settings.mcp_tls_insecure:
        parts.append("MCP_TLS_INSECURE=true")
    if settings.mcp_tls_ca_certs:
        parts.append(f"MCP_TLS_CA_CERTS={settings.mcp_tls_ca_certs}")
    return ", ".join(parts) if parts else "default (verify TLS certificates)"


def build_server_context_hints(name: str, settings: Settings, params: StdioServerParameters) -> list[str]:
    """Non-secret configuration context for a failed MCP server check."""
    hints: list[str] = []
    url = extract_mcp_remote_url(params.args)
    if url:
        hints.append(f"URL: {url}")
    hints.append(f"Command: {format_mcp_remote_command(params)}")
    hints.append(f"TLS: {_tls_summary(settings)}")

    if name == "splunk_o11y":
        hints.append(f"SPLUNK_O11Y_REALM: {settings.splunk_o11y_realm or 'missing'}")
        hints.append(f"SPLUNK_O11Y_API_TOKEN: {_credential_status(settings.splunk_o11y_api_token)}")
    elif name == "splunk_cloud_mcp":
        hints.append(
            "SPLUNK_CLOUD_MCP_BEARER_TOKEN: "
            f"{_credential_status(settings.splunk_cloud_mcp_bearer_token)}"
        )
        tenant = settings.splunk_cloud_mcp_tenant
        hints.append(f"SPLUNK_CLOUD_MCP_TENANT: {tenant if tenant else 'missing'}")
    elif name == "splunk_enterprise_mcp":
        hints.append(f"SPLUNK_MCP_BEARER_TOKEN: {_credential_status(settings.splunk_mcp_bearer_token)}")

    return hints


def hints_for_mcp_error(
    message: str,
    *,
    server_name: str,
    settings: Settings,
    params: StdioServerParameters,
) -> list[str]:
    """Actionable troubleshooting hints for a failed MCP connectivity check."""
    hints = build_server_context_hints(server_name, settings, params)
    lowered = message.lower()

    if "connection closed" in lowered or "closedresourceerror" in lowered:
        hints.extend(
            [
                "mcp-remote exited before the MCP handshake finished.",
                "Common causes: wrong MCP URL, expired/invalid token, missing splunk_tenant "
                "(Cloud MCP), or the MCP server refused the connection.",
                "Verify facilitator env vars: echo $SPLUNK_O11Y_GATEWAY_URL $SPLUNK_CLOUD_MCP_URL",
            ]
        )
        if server_name == "splunk_cloud_mcp" and not settings.splunk_cloud_mcp_tenant:
            hints.append(
                "SPLUNK_CLOUD_MCP_TENANT is not set — Splunk Cloud MCP usually requires "
                "the splunk_tenant header."
            )

    url = extract_mcp_remote_url(params.args)
    if url:
        probe = probe_mcp_url_reachability(url, settings)
        if probe:
            hints.append(f"HTTP probe: {probe}")

    return hints


def probe_mcp_url_reachability(url: str, settings: Settings) -> str | None:
    """Best-effort GET to see whether the MCP host responds (no auth headers)."""
    context = ssl.create_default_context()
    if settings.mcp_tls_insecure:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10, context=context) as response:
            return f"{response.status} from {url}"
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403, 405}:
            return (
                f"HTTP {exc.code} from {url} — host reachable; failure is likely auth "
                "headers or token expiry"
            )
        return f"HTTP {exc.code} from {url}"
    except urllib.error.URLError as exc:
        return f"could not reach {url}: {exc.reason}"
    except OSError as exc:
        return f"could not reach {url}: {exc}"


async def capture_mcp_remote_stderr(
    params: StdioServerParameters,
    *,
    timeout_seconds: float = 8.0,
) -> str | None:
    """
    Run mcp-remote once and return stderr (excluding Node TLS warnings).

    Used when the MCP client only reports 'Connection closed'.
    """
    env = os.environ.copy()
    if params.env:
        env.update(params.env)

    proc = await asyncio.create_subprocess_exec(
        params.command,
        *params.args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        _, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
    except TimeoutError:
        proc.kill()
        await proc.communicate()
        return "mcp-remote did not exit within 8s (stdio waiting — URL may be reachable)"

    stderr = stderr_bytes.decode(errors="replace").strip()
    if not stderr:
        return None

    lines = [
        line
        for line in stderr.splitlines()
        if "NODE_TLS_REJECT_UNAUTHORIZED" not in line and "Use `node --trace-warnings" not in line
    ]
    if not lines:
        return None
    return "; ".join(lines[:4])
