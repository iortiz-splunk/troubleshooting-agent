"""Resolve Splunk Observability environment and log index from settings and alert context."""

from __future__ import annotations

from typing import Any

from workshop_shared.config import Settings


def append_workshop_targets_prompt(base_prompt: str, settings: Settings) -> str:
    """Append configured O11y environment and Splunk index defaults to a system prompt."""
    return (
        f"{base_prompt}\n\n"
        "## Workshop tenant defaults\n\n"
        "Use these when the alert payload, user message, or investigation metadata "
        "do not specify an environment or Splunk index:\n"
        f"- APM **params.environment_name**: `{settings.splunk_o11y_environment}`\n"
        f"- Splunk log search **index=**: `{settings.splunk_search_index}`\n"
        "When alert context includes sf_environment or a specific index, prefer those values."
    )


def resolve_o11y_environment(
    *,
    settings: Settings,
    alert: dict[str, Any] | None = None,
    investigation_metadata: dict[str, str] | None = None,
) -> str:
    """Return APM environment_name: alert → metadata → settings default."""
    environment = ""
    if alert:
        props = alert.get("customProperties")
        if isinstance(props, dict):
            environment = str(props.get("sf_environment") or "").strip()
        if not environment:
            environment = str(alert.get("sf_environment") or "").strip()
    meta = investigation_metadata or {}
    if not environment:
        environment = str(meta.get("environment") or "").strip()
    if not environment:
        environment = settings.splunk_o11y_environment.strip()
    return environment


def resolve_splunk_search_index(
    *,
    settings: Settings,
    catalog: dict[str, Any] | None = None,
    product_type: str | None = None,
) -> str:
    """Return Splunk index: settings default, unless catalog defines a product override."""
    index = settings.splunk_search_index.strip()
    if not catalog:
        return index

    products = catalog.get("products")
    if not isinstance(products, dict):
        return index

    key = (product_type or "").strip().lower()
    product = products.get(key) if key else None
    if isinstance(product, dict):
        primary = str(product.get("primary_index") or "").strip()
        if primary and primary != str(catalog.get("default_index") or "").strip():
            return primary

    catalog_default = str(catalog.get("default_index") or "").strip()
    if catalog_default and catalog_default != settings.splunk_search_index:
        return settings.splunk_search_index

    return index
