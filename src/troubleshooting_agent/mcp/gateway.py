"""Build StdioServerParameters for mcp-remote (matches Cursor MCP config)."""

from mcp import StdioServerParameters

from troubleshooting_agent.config import Settings


def _build_mcp_remote_args(settings: Settings, url: str, extra_headers: list[str]) -> list[str]:
    """Shared mcp-remote argv prefix."""
    args = [
        "-y",
        "mcp-remote",
        url,
        "--silent",
        *extra_headers,
    ]
    if settings.mcp_allow_http:
        args.extend(["--transport", "http-only", "--allow-http"])
    return args


def splunk_o11y_gateway_params(settings: Settings) -> StdioServerParameters:
    """
    Splunk Observability Cloud via the Splunk Cloud MCP gateway.

    Requires only Observability credentials: X-SF-REALM and X-SF-TOKEN.
    """
    if not settings.splunk_o11y_gateway_url:
        msg = "SPLUNK_O11Y_GATEWAY_URL is required"
        raise ValueError(msg)
    if not settings.splunk_o11y_realm:
        msg = "SPLUNK_O11Y_REALM is required"
        raise ValueError(msg)
    if not settings.splunk_o11y_api_token:
        msg = "SPLUNK_O11Y_API_TOKEN is required"
        raise ValueError(msg)

    headers = [
        "--header",
        f"X-SF-REALM:{settings.splunk_o11y_realm}",
        "--header",
        f"X-SF-TOKEN:{settings.splunk_o11y_api_token}",
    ]

    return StdioServerParameters(
        command=settings.mcp_npx_command,
        args=_build_mcp_remote_args(settings, settings.splunk_o11y_gateway_url, headers),
    )


def splunk_cloud_mcp_params(settings: Settings) -> StdioServerParameters:
    """
    Splunk Cloud MCP server via mcp-remote (platform / logs, not Observability-only).

    Requires Authorization Bearer and splunk_tenant per Splunk Cloud MCP docs.
    """
    if not settings.splunk_cloud_mcp_url:
        msg = "SPLUNK_CLOUD_MCP_URL is required"
        raise ValueError(msg)
    if not settings.splunk_cloud_mcp_bearer_token:
        msg = "SPLUNK_CLOUD_MCP_BEARER_TOKEN is required"
        raise ValueError(msg)

    headers = [
        "--header",
        f"Authorization: Bearer {settings.splunk_cloud_mcp_bearer_token}",
    ]
    if settings.splunk_cloud_mcp_tenant:
        headers.extend(["--header", f"splunk_tenant:{settings.splunk_cloud_mcp_tenant}"])

    return StdioServerParameters(
        command=settings.mcp_npx_command,
        args=_build_mcp_remote_args(settings, settings.splunk_cloud_mcp_url, headers),
    )


def splunk_enterprise_mcp_params(settings: Settings) -> StdioServerParameters:
    """Splunk Enterprise MCP via mcp-remote (on-prem endpoint)."""
    if not settings.splunk_mcp_url:
        msg = "SPLUNK_MCP_URL is required"
        raise ValueError(msg)
    if not settings.splunk_mcp_bearer_token:
        msg = "SPLUNK_MCP_BEARER_TOKEN is required"
        raise ValueError(msg)

    headers = [
        "--header",
        f"Authorization: Bearer {settings.splunk_mcp_bearer_token}",
    ]

    return StdioServerParameters(
        command=settings.mcp_npx_command,
        args=_build_mcp_remote_args(settings, settings.splunk_mcp_url, headers),
    )
