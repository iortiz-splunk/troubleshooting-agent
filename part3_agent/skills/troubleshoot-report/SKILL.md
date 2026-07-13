---
name: troubleshoot-report
description: Formats troubleshooting and root-cause findings into a consistent report with alert context, timestamps, links, concise RCA, and next steps. Use when finishing an investigation, or when the user asks for a summary, handoff, RCA, or next steps after troubleshooting any alert or incident (any toolchain).
---

# Troubleshoot report (standard output)

Apply at the **end** of any troubleshooting workflow so responses stay consistent and easy to hand off. Tool-agnostic: use whatever identifiers and URLs the integrated systems return (e.g. Observability MCP, Splunk, future APIs).

---

## When to use

- Investigation is **done** or **paused** and the user should get a structured summary.
- User asks for **RCA**, **summary**, **next steps**, or **documentation** of the issue.

---

## Required sections

Use this template in order. Omit a section only if there is truly no data; say **Unknown** or **N/A** briefly rather than inventing details.

### 1. Alert / incident

- **Name / detector**: Human-readable detector or rule name (and label if different).
- **Severity** (if known).
- **Scope / product** (if known): e.g. APM service, infra host, RUM app, synthetic check—use labels that match your tools.

### 2. Identifiers

- Stable IDs from the source system(s): e.g. incident, detector, event, trace, ticket. Use the field names your tools expose.
- If the user may see the same value under another name (e.g. UI `noteId` vs API `incidentId`), note that once under **Identifiers** or **Notes**.

### 3. Timestamps

- **Alert or state change time** (primary).
- **Investigation window** used for queries (if different), in UTC or with timezone stated.

### 4. Links

Grouped bullets; **only include URLs from tool responses or the user**—do not fabricate links.

- **Incident / alert / detector** (as available)
- **Dashboards or entity pages** (service, host, check, etc.)
- **Deep links** (traces, logs, runbooks) when present

### 5. Summary

- **2–4 sentences**: what fired, affected scope, and current status (ongoing vs recovered if known).

### 6. Root cause analysis (RCA)

- **Concise** bullets: main finding first.
- Mark **Confirmed** vs **Likely / hypothesis** when evidence is incomplete.
- Tie bullets to **evidence** (metric name, log pattern, trace id)—short, not a full dump.

### 7. Next steps

- **Numbered**, **actionable** items (verify in UI, change config, scale, open ticket, tune alert).
- Optional: owner or system (e.g. “Platform”, “App team”) if clear.

---

## Optional sections

Use when useful; see [reference.md](reference.md).

- **Evidence collected** — Tools or queries used (names only; no secrets).
- **Data gaps** — What was missing (tags, logs, permissions, time range).
- **Confidence** — Low / Medium / High for the primary RCA line.

---

## Rules

- **No fabricated URLs or IDs.**
- Prefer **UTC** for timestamps or state the timezone.
- Keep RCA **short**; move long tables or queries to an appendix or separate artifact if needed.