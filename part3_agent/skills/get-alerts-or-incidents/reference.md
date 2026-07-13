# get-alerts-or-incidents — Reference

Use for **field names**, **ID semantics**, and **manual table columns** when not using **`parse_alerts_response.py`**.

## IDs

| Concept | UI / response | MCP request |
|--------|----------------|-------------|
| **Detector ID** | URL `#/detector/<detectorId>/...`; field **`detectorId`** | **`detector_id`** |
| **Incident ID** | URL `incidentId=...`; field **`incidentId`** | No parameter — search time range + **`limit`**, match in **`alerts`** (same value as **`noteId`** in some UI views) |
| **Event ID** | Field **`eventId`** | Match in results only |

## Alert object (main fields)

| Field | Notes |
|-------|--------|
| `anomaly_state_update_iso_8601_date_time` | Display time |
| `anomalyStateUpdateTimestampMs` | Prefer for sort when present |
| `detectLabel` / `detector` | Detector name |
| `detectorId`, `incidentId`, `eventId` | Traceability |
| `active`, `anomalyState`, `severity` | Status |
| `originatingMetric`, `eventCategory`, `customProperties`, `link` | Context / URL |

## Manual Description column (if not using script)

Join **`eventCategory`**; **`metric: ` + `originatingMetric`**; from **`customProperties`**: **`host.name`**, **`k8s.pod.name`**, **`k8s.container.name`**, **`state`**; else **`link.text`**. Escape **`|`** in markdown cells.

## Parameters

**`time_range`** — ISO or relative (`-15m`, `-1h`, `-1d`, `-1w`). **`stop`** usually **`now`**.

**`limit`** — Hard cap per response; see SKILL **truncation** / **last N** rules.

**`keywords`** — Short label search only; not for hyphenated service names or environments.

**`service_name`**, **`environments`**, **`severity`**, **`detector_id`** — As in MCP schema.
