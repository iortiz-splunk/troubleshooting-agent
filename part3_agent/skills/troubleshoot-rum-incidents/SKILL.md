---
name: troubleshoot-rum-incidents
description: Guides troubleshooting of Real User Monitoring (RUM) alerts or incidents in Splunk Observability Cloud. Use when the user asks to troubleshoot, investigate, or find root cause for a RUM detector, front-end error, page/view, browser, session, slow page load or P99, or an incident whose scope is client-side (often with app, country, page/view in alert context).
---

# Troubleshoot RUM alerts or incidents

Use when the detector or incident is **RUM**-scoped (page/view, web/mobile app, browser, geo) rather than pure **APM** or **infrastructure**.

---

## 1. Load the alert

Apply **get-alerts-or-incidents**: MCP **`o11y_search_alerts_or_incidents`**. Prefer **`detector_id`** from the detector URL; for **incident-only** input, use progressive **`time_range`**, **`include_inactive: true`**, sufficient **`limit`**, match **`incidentId`**.

Extract from **`customProperties`** (and related fields): **`app`**, **`sf_environment`**, **`deployment.environment`**, **`sf_product`**, **`sf_node_name`**, **`sf_node_type`**, **`country`**, **`app.version`**, and any **browser** / **device** dimensions. Copy **`link.url`** when present.

---

## 2. Quantify tail latency and splits (O11y MCP)

Use **`o11y_get_metric_names`** with terms like **`rum`**, **`page_view`**, **`webvitals`**, **`lcp`**, **`long_task`** to discover **RUM metric names** (e.g. **`rum.page_view.time.ns.p99`**, **`rum.webvitals_lcp.time.ns.p99`**, **`rum.long_task.count`**).

Use **`o11y_get_metric_metadata`** on those metric names to see **dimensions** (e.g. **`app`**, **`country`**, **`sf_node_name`**, **`sf_ua_browsername`**, **`deployment.environment`**) before writing SignalFlow.

Use **`o11y_execute_signalflow_program`** (and **`o11y_generate_signalflow_program`** if you need help) to:

- Filter **`filter('app', '<rum_app_name>')`** matching the incident **`app`**.
- Compare **tail** vs **median**: **`p99`** (and **`p75`**) for page load / Web Vitals.
- **Split** by **`country`**, **`sf_node_name`**, **`sf_ua_browsername`** — often **one geo or route** drives **P99** while the global average looks fine.
- **Correlate** high **`rum.long_task.count`** (by **`country`** or **`app`**) with **slow P99** — **long tasks** on the main thread are a common **tail-latency** driver.

If a **by-dimension** series is **empty**, the dimension may be **sparse** or named differently — **drill in the RUM UI** for **page/view** breakdowns.

---

## 3. Relate to APM (backend)

**`deployment.environment`** (and sometimes **`sf_environment`**) on RUM often aligns with an **APM environment** name. Use **`o11y_get_apm_environments`** with that **`environment_name`**; then **`o11y_get_apm_services`**, **`o11y_get_apm_service_latency`**, **`o11y_get_apm_exemplar_traces`** / **`o11y_get_apm_trace_tool`** for services that **serve the same product** (e.g. BFF/API gateways, checkout) when RUM shows **slow or failing fetches** or you need **origin** proof.

Apply **troubleshoot-apm-incidents** when the investigation shifts to **service traces** and **dependencies**.

---

## 4. Logs (Splunk MCP) — required before concluding

Apply **search-logs** when **`splunk_*` MCP tools** are connected. Use **`splunk_run_query`** with SPL scoped to the **RUM anomaly window** (UTC) and backend context from §3:

- Narrow by **index** / **sourcetype** (e.g. **`kube:container:*`**, **`httpevent`**) — use **`splunk_get_metadata`** if unknown.
- Correlate by **service name**, **pod**, **host**, **trace IDs** from APM, or **`deployment.environment`**.

**Do not** finish without at least one log search attempt (or an explicit note that Splunk MCP was unavailable).

---

## 6. Root cause and handoff

Summarize: **what changed** (release, route, geo, browser), **dominant metric** (e.g. **long tasks** + **IE**), **confidence**. Note **data gaps**.

**Final step (required):** **troubleshoot-report** — see [troubleshoot-report/SKILL.md](../troubleshoot-report/SKILL.md).

---

## More

- Metric names, dimensions, APM alignment: [reference.md](reference.md)
