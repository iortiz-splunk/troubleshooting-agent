---
name: investigation-report
description: Format the final investigation as a short handoff report. Always apply after MCP tools return — never paste raw JSON.
always_inject: true
---

# Investigation report (Part 2)

Apply this format for **every** final reply after tools have run. Tool JSON is for your analysis only — **do not** include raw MCP responses, `valueByTime` arrays, or full metric payloads in the user-facing answer.

## Required sections (use these headings)

### Alert / incident
- Detector or rule name, severity, service, environment (from alert search).

### Identifiers
- `eventId`, `incidentId`, `detectorId` when present in tool results.

### Summary
- 2–3 sentences: what fired, affected scope, active vs cleared if known.

### Findings
- 3–5 bullets with **interpreted** metrics only (e.g. "p99 ~1.8s, tail latency vs p50 ~0.6ms").
- Cite evidence briefly — metric names and values, not JSON dumps.

### Root cause (likely)
- 1–3 bullets marked **Likely** or **Confirmed** when evidence supports it.

### Next steps
- Numbered, actionable items (1–4). Optional: one follow-up query you could run.

## Rules

- **Never** paste raw tool JSON or time-series arrays in the reply.
- **Never** append "--- Observability data ---" blocks.
- Keep the full reply under ~800 words unless the user asks for detail.
- Use links from MCP results only — do not fabricate URLs.
- If data is missing, add a short **Data gaps** bullet instead of guessing.

## Workshop note (Part 2)

Part 3 adds exemplar traces, dependency drill-down, and a fuller `troubleshoot-report` skill. Part 2 stops at interpreted metrics + concise handoff.
