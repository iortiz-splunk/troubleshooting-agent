---
title: "Part 1 — Baseline Agent"
description: "Run the minimal MCP-only ReAct agent, interpret terminal and Galileo traces, and establish a baseline investigation for comparison with Parts 2 and 3."
weight: 6
navTitle: "Part 1 — Baseline Agent"
duration: "20 minutes"
---

Part 1 is the **baseline** — a minimal troubleshooting agent with **no skills and no multi-step workflow**. It runs a single LangGraph **ReAct loop**: the LLM reasons, calls Splunk Observability MCP tools when it needs data, observes the results, and repeats until it produces an answer.

The goal is not perfection. You are establishing what the agent does **without playbooks** so you can compare against Part 2 (skills) and Part 3 (structured graph).

## What Part 1 includes

| Component | Description |
|-----------|-------------|
| **Agent loop** | LangGraph ReAct: `agent` (LLM) → `tools` (MCP) → repeat |
| **Tools** | Splunk Observability MCP only (`o11y_*` prefix) |
| **Skills** | None — the model decides the investigation path on its own |
| **Observability** | Terminal trace, JSONL logs, Galileo session |

If you want to skim the code before running:

| File | Purpose |
|------|---------|
| `part1_agent/agent.py` | ReAct graph, MCP wiring, Galileo callbacks |
| `part1_agent/prompt.py` | System prompt — requires calling `o11y_*` tools for live data |

## Run your first investigation

Make sure you completed [Configure Agent Environment](/troubleshooting-agent/5-configure-agent-environment/) — virtual environment installed, `.env` configured, and both doctor commands passing.

Start with a CLI investigation using the workshop's default APM service:

{{< tabs >}}
{{% tab title="Script" open="true" %}}

```bash
cd ~/troubleshooting-agent
source .venv/bin/activate
cd part1_agent
troubleshooting-agent chat "Why is Verification slow?"
```

{{% /tab %}}
{{% tab title="Example Output" %}}

```text
══════════════════════════════════════════════════════════════
 Investigation  chat:a1b2c3d4  |  part1  |  cli
──────────────────────────────────────────────────────────────
 Query: Why is Verification slow?
 LLM: openai  |  MCP tools available: 12
══════════════════════════════════════════════════════════════
[1] LLM turn 1 — calling tools: o11y_search_alerts_or_incidents
[2] MCP o11y_search_alerts_or_incidents — OK (1.8 KB) | alerts=1
[3] LLM turn 2 — calling tools: o11y_get_apm_service_latency
[4] MCP o11y_get_apm_service_latency — OK (3.2 KB)
[5] LLM turn 3 — composing final response (512 chars)
──────────────────────────────────────────────────────────────
 Agent response
──────────────────────────────────────────────────────────────
- Active latency alert on Verification (production) ...
- p99 latency elevated vs baseline ...
- Recommended next steps: check recent deployments, inspect traces ...
══════════════════════════════════════════════════════════════
```

{{% /tab %}}
{{< /tabs >}}

You can also paste alert text from the facilitator's demo or substitute a different service name if instructed.

{{< notice title="Tip" style="tip" >}}
The facilitator may provide sample alert JSON or a specific investigation prompt. Use whatever scenario they share — the observability workflow is the same.
{{< /notice >}}

## Read the terminal trace

With `AGENT_LOG_TRACE=true` (the default), every run prints a structured trace to the terminal. As you read it, ask:

1. **Which MCP tools did the agent call?** — Look for `[n] MCP o11y_...` lines.
2. **Which tools did it skip?** — A baseline agent often skips traces, logs, or infrastructure correlation.
3. **Were parameters correct?** — Service names should be exact (e.g. `Verification`, not split keywords). Time ranges should use `{"start": "-1h", "stop": "now"}` inside a `params` object.
4. **Is the answer grounded?** — Does the final response reflect actual JSON from tool results, or does it sound plausible without evidence?

The same events are written to `shared/logs/investigations/<id>.jsonl` for post-workshop review.

## Review the run in Galileo

After your chat completes, open the Galileo console (URL from your `.env` — typically the multitenant workshop console) and navigate to:

1. **Project** — the name you set (`workshop-<your-instance>`)
2. **Log stream** — the name you set (`part1-<your-instance>`)
3. **Sessions** — find the most recent session (named `chat:... | part1_agent`)

Expand the trace tree. In Part 1 you should see:

```text
part1_investigation
├── agent          ← LLM turn (may repeat)
├── tools          ← MCP tool execution (may repeat)
└── session_usage  ← token totals for the run
```

Click into tool spans to see MCP inputs and outputs. Compare what Galileo captured with what the terminal trace showed — they should tell the same story.

{{< notice title="Tip" style="tip" >}}
Keep the Galileo console open in a browser tab during the workshop. After each investigation, refresh and locate your session — it is the fastest way to compare Part 1, Part 2, and Part 3 on the same alert.
{{< /notice >}}

## Baseline exercise

Work through this checklist with the investigation prompt your facilitator provides (latency on **Verification** is the default):

| Step | Action |
|------|--------|
| 1 | Run `troubleshooting-agent chat` with the workshop alert or query |
| 2 | Read the terminal trace — list tools called vs. tools skipped |
| 3 | Open Galileo — find your session and expand agent/tool spans |
| 4 | Answer: *Did the agent ground its conclusion in MCP data?* |
| 5 | Answer: *Where might it have hallucinated if MCP had returned empty results?* |
| 6 | **Save your notes** — you will re-run the same scenario in Part 2 and Part 3 |

{{< notice title="Important" style="primary" >}}
Part 1 intentionally has **no playbook**. Expect variation between runs — that is the baseline you are measuring. Parts 2 and 3 add skills and structure to make investigations repeatable.
{{< /notice >}}

## What you learned

- Part 1 proves the agent **can** call live Observability MCP tools and synthesize an answer.
- Without skills, **tool selection and investigation depth vary** from run to run.
- **Terminal traces** give immediate feedback; **Galileo** preserves the full session for review and comparison.
- This baseline sets up the core workshop question: *How much do skills and graph structure improve investigation quality?*

---

**Next:** Part 2 — Skill Playbooks (coming soon) — see how keyword-injected `SKILL.md` files change what the agent investigates and in what order.
