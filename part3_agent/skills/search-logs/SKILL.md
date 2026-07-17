---
name: search-logs
description: Search Splunk platform logs via Splunk Cloud or Enterprise MCP before concluding an investigation. Use splunk_run_query with efficient SPL built from alert context (service, environment, time window, K8s/host tags).
---

# Search logs (Splunk MCP) — required before concluding

**Do not finish the investigation** until you have attempted at least one **Splunk platform log search** when **`splunk_*` MCP tools** are available in your tool list.

If no Splunk platform MCP tools are bound (only `o11y_*`), skip this step and note **Logs: not searched (Splunk MCP not connected)** in your summary.

---

## When this applies

- After O11y metrics/traces for the alert are gathered (APM, IM, RUM, or Synthetics).
- **Before** writing your final investigation summary or handing off to **troubleshoot-report**.

---

## Splunk MCP tools (platform — not `o11y_*`)

| Tool | Use |
|------|-----|
| **`splunk_run_query`** | **Primary** — run read-only SPL; returns events (≤1000) or stats. |
| **`splunk_get_indexes`** | **Fallback only** — when catalog queries return zero rows. |
| **`splunk_get_metadata`** | **Fallback only** — narrow sourcetypes when catalog + first query fail. |
| **`splunk_get_index_info`** | Confirm an index exists before searching it. |
| **`saia_generate_spl`** | Optional — natural language → SPL when you need help; **always review and tighten** filters before running. |
| **`saia_optimize_spl`** | Optional — improve a draft SPL for performance. |

**Guardrails:** `splunk_run_query` is for **non-destructive** searches only; keep runtime under ~1 minute; prefer **`head`** / **`stats`** over raw export.

---

## Catalog-first workflow (mandatory order)

1. **Read the index catalog** injected in your investigate prompt (`indexes.md` for this tenant) — use **`default_index`** and product **sourcetypes** there.
2. **Collect O11y context** (service, environment, optional pod/host/trace tags from APM tools).
3. **`splunk_run_query`** with scoped SPL using the catalog index — at least **one** query; prefer **two** if the first returns zero rows (widen time or drop sourcetype).
4. **Discovery fallback** — only if catalog queries return zero rows: `splunk_get_indexes` → `splunk_get_metadata` → retry with a wider filter.
5. **Summarize log findings** in the investigation output: patterns, error counts, example messages (redact secrets).
6. If all queries return **zero events**, say so and list which filters were tried — do **not** invent log lines.

---

## Build efficient SPL from alert context

Use identifiers already parsed from the alert or APM trace tags. **Never** run unbounded `index=*` without a tight **`earliest`/`latest`** window.

### 1. Time window (always first)

- Prefer the alert **`anomaly_state_update_iso_8601_date_time`** (or Slack investigation window) as the center.
- Default SPL bounds: **`earliest=-30m latest=+5m`** relative to alert time, or **`earliest=-1h latest=now`** when only relative time is known.

### 2. Scope filters (pick what you have)

| Source | SPL filter examples |
|--------|---------------------|
| **APM service** (`sf_service`) | `sourcetype="kube:container:<lowercase-service>"` OR `_raw="*Verification*"` in `httpevent` / `json` |
| **Environment** (`sf_environment`) | May be absent in logs — prefer pod/namespace from APM trace tags |
| **K8s from alert/trace** | `k8s.namespace.name="..."`, `k8s.pod.name="..."`, search `_raw="*pod-name*"` in `kube:events` |
| **Trace correlation** | `trace_id="<from o11y_get_apm_exemplar_traces>"` in `kube:container:*` or `json` |
| **HTTP / latency** | `http.resp.status>=400`, `http.resp.took_ms>1000`, `_raw="*timeout*"` |

Combine with **`AND`**; start **narrow** (index + sourcetype + time), then widen once if zero results.

### 3. Example SPL patterns (o11y-workshop-amer — adapt from catalog)

**APM service errors (catalog index):**
```spl
index=splunk4rookies-workshop earliest=-1h latest=now
(sourcetype="kube:container:paymentservice" OR sourcetype=httpevent)
(severity=error OR http.resp.status>=400 OR _raw="*error*")
| head 50
```

**Trace ID from exemplar:**
```spl
index=splunk4rookies-workshop earliest=-1h latest=now
trace_id="<trace_id_from_apm>"
| head 50
```

**K8s pod restart (IM):**
```spl
index=splunk4rookies-workshop earliest=-1h latest=now
sourcetype=kube:events _raw="*<pod-name>*"
| head 50
```

**Quick volume check:**
```spl
index=splunk4rookies-workshop earliest=-1h latest=now
sourcetype=httpevent
| stats count by sourcetype
```

---

## Final step

Include log evidence (or explicit **no logs found** / **Splunk MCP unavailable**) before applying **troubleshoot-report**.

More field-name hints: [reference.md](reference.md). Facilitator index catalog: [indexes.md](indexes.md).
