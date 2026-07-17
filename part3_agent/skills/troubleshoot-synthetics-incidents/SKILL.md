---
name: troubleshoot-synthetics-incidents
description: Guides troubleshooting of Splunk Observability Synthetics alerts and incidents (browser checks, API checks, journeys, uptime). Use when the user asks to troubleshoot synthetic checks, failing journeys, availability, SSL, or latency from Synthetics detectors, or when alert context points to synthetics metrics or check names.
---

# Troubleshoot Synthetics alerts or incidents

Use for **Synthetic Monitoring** failures or degradations (check/journey/availability), not for **RUM** (real users) unless correlating both.

---

## 1. Load the alert

Apply **get-alerts-or-incidents**: MCP **`o11y_search_alerts_or_incidents`**. Prefer **`detector_id`** from the URL; otherwise progressive **`time_range`**, **`include_inactive: true`**, **`limit`**, match **`incidentId`**.

Extract from **`customProperties`** (varies by detector): **check / journey / test name**, **location** or **probe**, **target URL or host**, **HTTP** or **assert** context, **`sf_service`** or app tags if present. Copy **`link.url`** when present.

---

## 2. Quantify with metrics (O11y MCP)

Use **`o11y_get_metric_names`** with terms like **`synthetics`**, **`synthetic`**, **`check`**, **`duration`**, **`failure`** to find **SignalFlow**-addressable series (e.g. **`synthetics.duration.time.ms`**, **`synthetics.resource_request.count`**, **`synthetics.resource_request.size.bytes`** — exact names depend on org).

Use **`o11y_get_metric_metadata`** on selected metrics to list **dimensions** (e.g. **check name**, **location**, **target**, **integration**).

Use **`o11y_execute_signalflow_program`** / **`o11y_generate_signalflow_program`** to:

- Plot **duration**, **failure** / **success** trends in the **incident window**.
- **Split** by **location** and **check** (or equivalent dimensions) — **one region** or **one step** often explains intermittent alerts.
- Compare **before vs during** the anomaly on the **same** check.

If series are **empty**, widen **time**, confirm **metric name** spelling, or use **Synthetics UI** for the run detail.

---

## 3. Correlate with APM, IM, and logs

| Signal | When to use |
|--------|-------------|
| **APM** | The check hits an **HTTP**/**API** you own — map **URL/host** to **service** + **`sf_environment`**; **`o11y_get_apm_services`**, **latency**, **exemplar traces** / **`o11y_get_apm_trace_tool`** in the **failure window**. Use **troubleshoot-apm-incidents** for deep service analysis. |
| **IM** | Suspect **probe-side network**, **DNS**, **regional** reachability, or **target host** saturation — **host**, **k8s**, **network** metrics (**troubleshoot-im-incidents**), aligned by **time** and **target** if known. |
| **Logs (Splunk MCP)** | **Required before concluding** — apply **search-logs**: **`splunk_run_query`** for **target** app/gateway logs during failures; scope time, index, service, pod, path, or status. |

Synthetics proves **reachability and timing** from **outside-in**; **APM/IM/logs** explain **why** the **stack** misbehaved.

---

## 5. Root cause and handoff

Summarize: **failing check/journey**, **location** pattern, **metric** (duration vs availability vs resource), **downstream** owner (app vs network). Note **data gaps**.

**Final step (required):** **troubleshoot-report** — [troubleshoot-report/SKILL.md](../troubleshoot-report/SKILL.md).

---

## More

- Metric patterns and correlation detail: [reference.md](reference.md)
