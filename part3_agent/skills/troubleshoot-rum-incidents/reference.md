# troubleshoot-rum-incidents — Reference

## Alert dimensions (typical)

| Field (examples) | Use |
|------------------|-----|
| `app` | RUM application name — filter metrics and RUM UI |
| `deployment.environment` | Often maps to **APM environment** name for backend correlation |
| `sf_environment` | Additional environment label (may differ from `deployment.environment`) |
| `sf_product` | e.g. `web` / `mobile` |
| `sf_node_name` | Route, page, or view identifier |
| `sf_node_type` | e.g. `view` |
| `country` | Geo slice |
| `app.version` | Release correlation |

Read **`customProperties`** from **`o11y_search_alerts_or_incidents`**; keys vary by detector.

## RUM metrics (examples)

| Pattern | Typical use |
|---------|-------------|
| `rum.page_view.time.ns.p99` / `.p75` | Page navigation timing — **tail** vs **median** |
| `rum.webvitals_lcp.time.ns.p99` (and related) | **LCP** / paint — compare with **page_view** if story differs |
| `rum.long_task.count` | **Main-thread** blocking — **sum** or **rate** by **`country`** / **`app`** |

Discover exact names with **`o11y_get_metric_names`**; confirm dimensions with **`o11y_get_metric_metadata`**.

## APM ↔ RUM alignment

1. Read **`deployment.environment`** (and **`sf_environment`**) from the alert or **metric metadata** `app` subset.
2. **`o11y_get_apm_environments`** with **`environment_name`** set to that value (if it exists).
3. **`o11y_get_apm_services`** with **`environment_name`** + optional **`service_name`** for known backends (from architecture or traces).

If the **APM** environment name differs from the RUM label, use **service names** or **tags** from **traces** / **docs** to link workloads.

## Splunk logs (MCP)

- Scope **time** to the **RUM** spike window (**UTC**).
- Prefer **structured** filters: **sourcetype**, **host**, **pod**, **service** from APM traces or Kubernetes metadata.
- **search-logs/indexes.md** lists **indexes** and **`kube:container:*`** patterns for this environment.

## Related skills

- **get-alerts-or-incidents** — progressive windows, **`parse_alerts_response.py`**
- **troubleshoot-apm-incidents** — traces and service latency
- **troubleshoot-report** — final report
