"""Normalize Splunk MCP endpoint URLs from workshop env vars."""

from __future__ import annotations

from urllib.parse import urlparse

SPLUNK_MCP_SERVER_PORT = ":8089"
SPLUNK_MCP_SERVER_PATH = "/services/mcp"
SPLUNK_CLOUD_MCP_GATEWAY_PATH = "/system/mcp-gateway/v1/"


def is_splunk_cloud_api_gateway_host(url: str | None) -> bool:
    """
    True for Splunk Cloud API gateway hosts used by Observability MCP.

    Example: ``region-pdx10.api.scs.splunk.com``
    """
    if not url:
        return False
    host = (urlparse(url).hostname or "").lower()
    return bool(host) and host.endswith(".api.scs.splunk.com")


def is_direct_splunk_mcp_server_host(url: str | None) -> bool:
    """
    True for direct Splunk Cloud MCP server hosts (not the O11y API gateway).

    Example: ``mcp-shw-60c529e5624115.stg.splunkcloud.com``
    """
    if not url:
        return False
    host = (urlparse(url).hostname or "").lower()
    return host.startswith("mcp-")


# Backward-compatible alias for diagnostics imports.
is_legacy_splunk_cloud_api_gateway_host = is_splunk_cloud_api_gateway_host


def normalize_splunk_mcp_server_url(url: str | None) -> str | None:
    """
    Ensure direct Splunk MCP URLs use the MCP server endpoint:

    ``https://<host>:8089/services/mcp``

    Used for Splunk Cloud MCP (``mcp-*.stg.splunkcloud.com``) and Enterprise.
    Legacy ``/system/mcp-gateway/v1/`` URLs on direct MCP hosts are rewritten.
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


def normalize_splunk_o11y_gateway_url(url: str | None) -> str | None:
    """
    Ensure Observability MCP uses the Splunk Cloud API gateway endpoint.

    ``https://region-*.api.scs.splunk.com/system/mcp-gateway/v1/``

    Observability auth (X-SF-REALM + X-SF-TOKEN) goes through this gateway — not
    the direct MCP server URL used by ``SPLUNK_CLOUD_MCP_URL``.
    """
    if not url:
        return None
    value = url.strip()
    if not value:
        return None
    lowered = value.lower()
    if "/system/mcp-gateway" in lowered:
        return value

    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if host.startswith("mcp-"):
        # Wrong host for O11y, but never rewrite to SPLUNK_CLOUD_MCP_URL.
        return value

    if is_splunk_cloud_api_gateway_host(value):
        scheme = parsed.scheme or "https"
        return f"{scheme}://{host}{SPLUNK_CLOUD_MCP_GATEWAY_PATH}"

    if SPLUNK_MCP_SERVER_PATH not in lowered:
        base = value.rstrip("/")
        return f"{base}{SPLUNK_CLOUD_MCP_GATEWAY_PATH}"

    return value


normalize_splunk_cloud_mcp_url = normalize_splunk_mcp_server_url
normalize_splunk_enterprise_mcp_url = normalize_splunk_mcp_server_url
