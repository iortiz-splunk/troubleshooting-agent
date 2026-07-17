---
name: troubleshoot
description: Guides troubleshooting and root cause analysis for alerts and incidents in Splunk Observability Cloud. Use when the user asks to troubleshoot, investigate, or find the root cause of an alert or incident.
---

# Troubleshoot (router) — Splunk Observability alerts and incidents

**Always apply this skill** when the request matches [When to apply](#when-to-apply). It orchestrates **get-alerts-or-incidents** → product workflow → **troubleshoot-report**—do not skip to ad hoc MCP calls without following the steps below.

---

## When to apply

**Use this skill** if **any** of these are true:

| Signal | Examples |
|--------|----------|
| **Verbs** | troubleshoot, investigate, diagnose, root cause, RCA, why is this firing, what's broken |
| **Entities** | alert, incident, detector, firing, anomalous, violation |
| **IDs** | `incidentId`, `eventId` (including from `?eventId=` URLs), `noteId` (same as `incidentId` in some UIs), `detector_id` / detector URL path |
| **Product context** | Splunk Observability, O11y, SignalFx, `signalfx.com`, APM service + environment in an incident |
| **Links** | `#/alerts`, `#/detector/`, `incidentId=` in query string |

**Edge case:** User pastes **only** a service name and "slow" with **no** alert — offer APM investigation via **troubleshoot-apm-incidents** or clarify; use **troubleshoot** if they confirm an alert/incident exists.

---

## Workflow (mandatory order)

```
1. Identify alert  →  2. Categorize product  →  3. Run product skill  →  4. troubleshoot-report
```

Copy this checklist and complete it:

- [ ] **1. Identify** — Full alert payload (or documented failure to load); see §1.
- [ ] **2. Categorize** — IM / APM / RUM / Synthetics; see §2 and [reference.md](reference.md).
- [ ] **3. Execute** — **troubleshoot-apm-incidents**, **troubleshoot-im-incidents**, or RUM/Synthetics path.
- [ ] **3b. Logs** — **search-logs** via Splunk MCP (`splunk_run_query`) before concluding; required when `splunk_*` tools are connected.
- [ ] **4. Report** — **troubleshoot-report** (required every time, including partial investigations).

---

## 1. Identify the alert

Apply **get-alerts-or-incidents** (MCP tool: `o11y_search_alerts_or_incidents` with a `params` object).

| User input | Action |
|------------|--------|
| **Detector ID** or URL with `/detector/<id>/` | Set **`detector_id`** + **`time_range`** + **`include_inactive: true`**. |
| **Incident ID** / **noteId** | Wide **`time_range`**, **`include_inactive: true`**, raise **`limit`**; match **`incidentId`** on returned alerts. |
| **`eventId=`** in URL | MCP has **no `eventId` filter**—scan returned alerts for **`eventId`** (and **`id`**) match; widen window/limit if missing. |
| **APM `sf_service`** (+ optional **`sf_environment`**) | Set **`service_name`** (exact); optional **`environments`**. Never use **`keywords`** for service names. |
| **Vague text** | **`keywords`**: 1–2 words; if empty, retry **without** keywords and/or widen **`time_range`**. |

Extract from the payload for step 2: `detector`, `detectLabel`, `detectorId`, `incidentId`, `eventId`, `originatingMetric`, `severity`, `customProperties`, `anomaly_state_update_iso_8601_date_time`, `link`.

**If the alert cannot be loaded:** State that in **troubleshoot-report** under Summary / Data gaps; still give **next steps** (paste full incident URL, detector id, service/env from UI). Do **not** invent metrics or links.

---

## 2. Categorize the alert (product type)

| Product | Primary signals |
|--------|------------------|
| **IM** | `originatingMetric`: `k8s.*`, `system.*`, `container.*`, host/cpu/memory/disk; **customProperties**: `k8s.*`, `host.*`, `cloud.*` |
| **APM** | **`sf_service`** / latency-request-error patterns; detector text: service, latency, APM |
| **RUM** | RUM/app/page/session dimensions; detector: RUM, browser, mobile |
| **Synthetics** | Check/journey/availability; detector: synthetic |

**Order:** `originatingMetric` + `customProperties` first; then **detector** / **detectLabel**. Full table: [reference.md](reference.md).

---

## 3. Apply the right workflow

| Product | Skill / path |
|---------|----------------|
| **APM** | **troubleshoot-apm-incidents** (O11y MCP + Splunk logs as needed) |
| **IM** | **troubleshoot-im-incidents** (metrics + SignalFlow + logs) |
| **RUM** | **troubleshoot-rum-incidents** (alert context + RUM UI; APM if backend correlation) |
| **Synthetics** | **troubleshoot-synthetics-incidents** (metrics + UI; APM/IM/logs when correlating) |

---

## 4. Final report

Apply **troubleshoot-report** for every run (complete or blocked): identifiers, timestamps, links from tool responses only, summary, concise RCA, next steps.

---

## Reference

- Product classification detail: [reference.md](reference.md)
