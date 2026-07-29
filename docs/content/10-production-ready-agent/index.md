---
title: "Production-Ready Agent"
description: "Harden the Part 3 troubleshooting workflow for live incidents — alert intake, orchestration, MCP reliability, and operational guardrails."
weight: 10
navTitle: "Production-Ready Agent"
duration: "10 minutes"
---

After [Part 3 — Full Workflow]({{< ref "9-part3-full-workflow" >}}), you have a working four-node agent with skills, MCP tools, and Galileo tracing. Part 3 is a **teaching workflow** — the graph, skills, and MCP wiring are real, but several workshop shortcuts would need hardening before you run this on live incidents at scale.

This page summarizes practical next steps. It is optional reading — no lab steps required.

## Alert intake and context

- **Structured alert ingestion** — Replace mock CLI prompts with a durable trigger (Slack Events API, webhook, or queue consumer) and normalize every alert into a typed payload (`event_id`, `detector_id`, `service`, `environment`, `rule`, timestamps) before the graph starts.
- **Anchor IDs early** — Production runs should resolve the O11y alert record in code (like `fetch_alert_payload`) *before* the identify ReAct loop, so a bad LLM turn cannot burn tool budget searching for context.
- **Resolution / dedup** — Skip or shorten investigations when the alert is already cleared, or when the same `event_id` was handled recently.

## Orchestration and skills

- **Keep the graph; tighten the nodes** — The identify → categorize → investigate → report shape scales well. Production gains come from stricter node contracts (required outputs, max tool calls per node) and clearer handoff state between steps.
- **Hybrid routing** — The Python categorizer is fast and deterministic; add LLM fallback only for `unknown` product types, with explicit logging when routing is ambiguous.
- **Version and test playbooks** — Treat `SKILL.md` files like code: PR review, golden-path tests per product type, and Galileo evaluators (see [Galileo Logstream Evaluators]({{< ref "7-galileo-logstream-evaluators" >}})) on report structure and tool-use completeness.

## MCP, Splunk, and reliability

- **Session pooling and limits** — Workshop runs open MCP stdio sessions per investigation; production needs connection reuse, per-tenant rate limits, and timeouts so one slow query does not wedge the whole agent.
- **Catalog maintenance** — Keep `search-logs/indexes.md` (or a config service) aligned with your Splunk tenant; stale index names are a common source of “no logs found” false negatives.
- **Graceful degradation** — When Splunk MCP is down, return a partial report with O11y evidence and an explicit **Logs: unavailable** section instead of failing the run.

## Safety, trust, and operations

- **Human-in-the-loop for actions** — This agent is read-only (investigate + report). Any production extension that posts to Slack, opens tickets, or runs remediations should use a two-step confirm flow.
- **Secrets and tenancy** — API tokens via vault/KMS, not `.env` on shared hosts; scope MCP credentials per environment; redact tokens and PII in logs and Galileo traces.
- **Observability of the agent itself** — Session IDs, node timings, tool failure rates, and evaluator scores should feed dashboards and alerts — you are operating a service, not a one-off script.
- **Cost and latency budgets** — Set recursion limits, cap parallel MCP calls, and track LLM token usage per investigation; Part 3’s investigate node is the main cost driver.

{{< notice title="Workshop → production path" style="tip" >}}
A practical next step after the workshop: pick one alert type (e.g. APM error rate), wire real Slack or webhook intake, add one Galileo evaluator for **`troubleshoot-report`** completeness, and run shadow mode (agent reports, humans act) until scores stabilize.
{{< /notice >}}

## Related reading

- [Part 3 — Full Workflow]({{< ref "9-part3-full-workflow" >}}) — graph nodes and Galileo trace shape
- [AI Skills]({{< ref "2-ai-skills" >}}) — authoring and testing playbooks
- [Galileo Logstream Evaluators]({{< ref "7-galileo-logstream-evaluators" >}}) — quality gates for agent outputs
