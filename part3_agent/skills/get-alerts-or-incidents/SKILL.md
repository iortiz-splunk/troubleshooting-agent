---
name: get-alerts-or-incidents
description: Retrieves and formats alerts or incidents from Splunk Observability Cloud. Use when the user asks for alerts, incidents, detector triggers, or "what's firing" in O11y Cloud, or provides a detector ID, incident ID, or APM/RUM service name.
---

# Get alerts / incidents (Splunk Observability Cloud)

**MCP:** `o11y_search_alerts_or_incidents` · workshop MCP (o11y_* tools)

---

## Request workflow

1. **Time:** Start **`start: "-1h"`**, **`stop: "now"`**, **`include_inactive: true`**. Widen only if needed: **`-6h` → `-1d` → `-3d` → `-7d` → `-30d`** (then **`-90d`** only for long history or an **incident ID** still missing). Keep the same filters; only change **`start`**.

2. **`limit` (critical):** Each call returns **at most `limit`** alerts in **no guaranteed order**.
   - **“Last N” / “top N”:** Use **`limit` much larger than N** (e.g. **`500`**, or **`max(500, N×10)`** in very noisy orgs). Sort client-side, then take the first **N**.
   - **Truncation check:** If **`len(alerts) == limit`**, the window may be **cut off**—increase **`limit`**, narrow with **`detector_id`** / **`service_name`**, or widen time and accept you need multiple strategies.
   - **Fewer than N rows** after sort: widen the time ladder (step 1), not only `limit`.

3. **Sort (always before “most recent” or slicing):** Descending by **`anomalyStateUpdateTimestampMs`**; if missing, use parsed **`anomaly_state_update_iso_8601_date_time`**.

4. **Format:** Save MCP JSON and run **`parse_alerts_response.py`** (see below), or sort/slice in code when building a custom table.

---

## Scripts

Location: **`skills/get-alerts-or-incidents/scripts/`**

| Script | Role |
|--------|------|
| **`parse_alerts_response.py`** | Turn MCP **`{"alerts":[...]}`** JSON into a markdown table (stdin or file path). |

```bash
# Full table, newest first (default), optional caps
python3 skills/get-alerts-or-incidents/scripts/parse_alerts_response.py response.json
python3 .../parse_alerts_response.py --top 20 --with-ids --truncate 120 response.json
python3 .../parse_alerts_response.py --no-sort < response.json   # preserve API order
```

| Flag | Effect |
|------|--------|
| **`--top N`** | After sort, print only the first **N** rows (for “last N alerts”). |
| **`--with-ids`** | Add **`incidentId`**, **`eventId`**, **`detectorId`** columns. |
| **`--truncate M`** | Cap Description column length. |
| **`--no-sort`** | Skip reordering (default is newest state update first). |

---

## Lookup shortcuts

| User provides | MCP |
|---------------|-----|
| **Detector ID** (from `#/detector/<id>/...`) | **`detector_id`** — best filter. |
| **Incident / note ID** | No dedicated param — **`include_inactive: true`**, high **`limit`**, progressive window; match **`incidentId`**. Prefer **`detector_id`** from the same URL if present. |
| **APM/RUM service** | **`service_name`** = exact **`sf_service`**; optional **`environments`**. Do **not** put service names in **`keywords`**. |
| **Label keywords** | **`keywords`**: 1–2 single words; if no hits, retry **without** **`keywords`**. |

---

## More

- Response field list, **`noteId`**, and manual column mapping: **[reference.md](reference.md)**
