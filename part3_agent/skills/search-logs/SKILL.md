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

### `splunk_run_query` invocation (important)

**Do not** use a `params` object (that shape is for `o11y_*` tools only). Pass **flat** arguments:

```json
{
  "query": "index=k8s-apps sourcetype=\"kube:container:payment\" (severity=error OR _raw=\"*error*\") | head 50",
  "earliest_time": "-1h",
  "latest_time": "now",
  "row_limit": 50
}
```

Put the **time window in tool args** (`earliest_time`, `latest_time`), not ISO timestamps in the SPL string. See **Time windows** below.

**Response shape:** JSON with `results` (array of events), `total_rows`, and `truncated`. Each event includes `_raw`, `_time`, `sourcetype`, `source`, `host`, `index`. **Zero rows** returns `{"results":[],"total_rows":0}` — widen sourcetype or try `httpevent`, do not treat as a tool error.

**Efficiency:** call `splunk_run_query` at most **twice** per investigation (narrow SPL, then one widened retry). If both return zero rows, stop and document the gap — **do not** repeat the same SPL or call with empty `{}` / `params: {}`.

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

### 1. Time window (always first — read carefully)

**O11y and Splunk use different time formats.** Do not copy ISO timestamps from O11y alerts into Splunk SPL.

| Source | Valid format | Example |
|--------|--------------|---------|
| **O11y MCP** (`params.time_range`) | ISO 8601 OK | `{"start": "2026-07-30T14:17:20Z", "stop": "now"}` |
| **Splunk MCP tool args** | Relative or `now` | `"earliest_time": "-1h"`, `"latest_time": "now"` |
| **Splunk SPL `earliest=`/`latest=`** | Relative or `now` only | `earliest=-1h latest=now` |

**Invalid in Splunk SPL (returns 0 rows or validation error):**

```spl
earliest=2026-07-30T14:17:20.000Z latest=2026-07-30T14:57:20.000Z
```

**Recommended pattern (preferred):** omit `earliest`/`latest` from the SPL string; set time only on the tool call:

```json
{
  "query": "index=k8s-apps sourcetype=\"kube:container:payment\" _raw=\"*error*\" | head 50",
  "earliest_time": "-1h",
  "latest_time": "now",
  "row_limit": 50
}
```

**Alternative:** use the **same relative** bounds in both SPL and tool args:

```spl
index=k8s-apps earliest=-1h latest=now sourcetype="kube:container:payment" | head 50
```

**Alert timestamp handling:** use `anomaly_state_update_iso_8601_date_time` for **context in your summary only**. For log search, pick a relative window that covers the incident, e.g. `-1h`/`now` or `-40m`/`now` for a recent alert — **never paste the ISO string into SPL or `earliest_time`/`latest_time`**.

**Valid Splunk relative modifiers:** `-15m`, `-30m`, `-1h`, `-4h`, `-24h`, `-7d`, `now`.

### 2. Scope filters (pick what you have)

| Source | SPL filter examples |
|--------|---------------------|
| **APM service** (`sf_service`) | Map via catalog `service_aliases` (e.g. `paymentservice` → `kube:container:payment`). If zero rows, `httpevent` with `_raw="*<service>*"` or `trace_id` from exemplars |
| **Environment** (`sf_environment`) | May be absent in logs — prefer pod/namespace from APM trace tags |
| **K8s from alert/trace** | `k8s.namespace.name="..."`, `k8s.pod.name="..."`, search `_raw="*pod-name*"` in `kube:events` |
| **Trace correlation** | `trace_id="<from o11y_get_apm_exemplar_traces>"` in `kube:container:*` or `json` |
| **HTTP / latency** | `http.resp.status>=400`, `http.resp.took_ms>1000`, `_raw="*timeout*"` |

Combine with **`AND`**; start **narrow** (index + sourcetype + time), then widen once if zero results.

### 3. Example SPL patterns (o11y-workshop-amer — adapt from catalog)

**APM service errors (payment — time via tool args `-1h`/`now`):**
```spl
index=k8s-apps
(sourcetype="kube:container:payment" OR sourcetype=httpevent)
(severity=error OR http.resp.status>=400 OR _raw="*error*" OR _raw="*Invalid token*")
| head 50
```

**Widen when container sourcetype returns zero rows:**
```spl
index=k8s-apps
(sourcetype=httpevent OR sourcetype="kube:container:*")
_raw="*payment*"
| head 50
```

**Trace ID from exemplar:**
```spl
index=k8s-apps trace_id="<trace_id_from_apm>" | head 50
```

**K8s pod restart (IM):**
```spl
index=k8s-apps sourcetype=kube:events _raw="*<pod-name>*" | head 50
```

**Quick volume check:**
```spl
index=k8s-apps sourcetype=httpevent | stats count by sourcetype
```

---

## Final step

Include log evidence (or explicit **no logs found** / **Splunk MCP unavailable**) before applying **troubleshoot-report**.

More field-name hints: [reference.md](reference.md). Facilitator index catalog: [indexes.md](indexes.md).
