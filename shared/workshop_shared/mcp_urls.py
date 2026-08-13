"""Normalize Splunk MCP endpoint URLs from workshop env vars."""

from __future__ import annotations

from urllib.parse import urlparse

SPLUNK_MCP_SERVER_PORT = ":8089"
SPLUNK_MCP_SERVER_PATH = "/services/mcp"


def is_legacy_splunk_cloud_api_gateway_host(url: str | None) -> bool:
    """
    True for old Splunk Cloud API gateway hosts (not the direct MCP server).

    Example legacy host: ``region-pdx10.api.scs.splunk.com``
    Example MCP server host: ``mcp-shw-60c529e5624115.stg.splunkcloud.com``
    """
    if not url:
        return False
    host = (urlparse(url).hostname or "").lower()
    if not host or host.startswith("mcp-"):
        return False
    return host.endswith(".api.scs.splunk.com")


def normalize_splunk_mcp_server_url(url: str | None) -> str | None:
    """
    Ensure Splunk MCP URLs use the direct MCP server endpoint:

    ``https://<host>:8089/services/mcp``

    Workshop env vars sometimes provide only the hostname (with or without port).
    Legacy ``/system/mcp-gateway/v1/`` URLs are rewritten to the direct form using
    the same hostname. Full URLs that already include ``/services/mcp`` are unchanged.
    """
    if not url:
        return None
    value = url.strip()
    if not value:
        return None
    if SPLUNK_MCP_SERVER_PATH in value.lower():
        return value

    if "/system/mcp-gateway" in value.lower():
        parsed = urlparse(value)
        if parsed.hostname:
            scheme = parsed.scheme or "https"
            return f"{scheme}://{parsed.hostname}{SPLUNK_MCP_SERVER_PORT}{SPLUNK_MCP_SERVER_PATH}"
        return value

    base = value.rstrip("/")
    if ":8089" in base.lower():
        return f"{base}{SPLUNK_MCP_SERVER_PATH}"
    return f"{base}{SPLUNK_MCP_SERVER_PORT}{SPLUNK_MCP_SERVER_PATH}"


def align_o11y_gateway_url_with_cloud_mcp(
    o11y_url: str | None,
    cloud_url: str | None,
) -> str | None:
    """
    Point Observability MCP at the direct MCP server when o11y still uses a legacy API gateway host.

    Workshop EC2 images often set SPLUNK_O11Y_GATEWAY_URL to ``region-*.api.scs.splunk.com``
    while SPLUNK_CLOUD_MCP_URL already targets ``mcp-*.stg.splunkcloud.com:8089/services/mcp``.
    Both integrations use the same MCP server URL with different auth headers.
    """
    if not o11y_url or not cloud_url:
        return o11y_url
    if not is_legacy_splunk_cloud_api_gateway_host(o11y_url):
        return o11y_url
    o11y_host = (urlparse(o11y_url).hostname or "").lower()
    cloud_host = (urlparse(cloud_url).hostname or "").lower()
    if o11y_host == cloud_host:
        return o11y_url
    return cloud_url


normalize_splunk_cloud_mcp_url = normalize_splunk_mcp_server_url
normalize_splunk_o11y_gateway_url = normalize_splunk_mcp_server_url
normalize_splunk_enterprise_mcp_url = normalize_splunk_mcp_server_url
