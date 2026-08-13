"""Build StdioServerParameters for mcp-remote (matches Cursor MCP config)."""

from mcp import StdioServerParameters

from workshop_shared.config import Settings
from workshop_shared.mcp.command import resolve_mcp_npx_command


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


def mcp_remote_stdio_env(settings: Settings) -> dict[str, str] | None:
    """
    Optional Node.js env for the mcp-remote subprocess.

    mcp-remote uses Node fetch/HTTPS; self-signed staging certs need either a CA
    bundle (preferred) or MCP_TLS_INSECURE=true (workshop/staging only).
    """
    env: dict[str, str] = {}
    if settings.mcp_tls_ca_certs:
        env["NODE_EXTRA_CA_CERTS"] = settings.mcp_tls_ca_certs
    if settings.mcp_tls_insecure:
        env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
    return env or None


def _stdio_params(settings: Settings, args: list[str]) -> StdioServerParameters:
    return StdioServerParameters(
        command=resolve_mcp_npx_command(settings),
        args=args,
        env=mcp_remote_stdio_env(settings),
    )


def splunk_o11y_gateway_params(settings: Settings) -> StdioServerParameters:
    """
    Splunk Observability Cloud via the Splunk Cloud API gateway.

    Uses SPLUNK_O11Y_GATEWAY_URL (region-*.api.scs.splunk.com/system/mcp-gateway/v1/)
    with X-SF-REALM and X-SF-TOKEN — not the direct MCP server URL used for Cloud MCP.
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

    return _stdio_params(
        settings,
        _build_mcp_remote_args(settings, settings.splunk_o11y_gateway_url, headers),
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

    return _stdio_params(
        settings,
        _build_mcp_remote_args(settings, settings.splunk_cloud_mcp_url, headers),
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

    return _stdio_params(
        settings,
        _build_mcp_remote_args(settings, settings.splunk_mcp_url, headers),
    )
