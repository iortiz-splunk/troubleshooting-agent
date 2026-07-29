---
title: "Part 1 — Baseline Agent"
description: "Run the minimal MCP-only ReAct agent, interpret terminal and Galileo traces, and establish a baseline investigation for comparison with Parts 2 and 3."
weight: 6
navTitle: "Part 1 — Baseline Agent"
duration: "20 minutes"
---

Part 1 is the **baseline** — a minimal troubleshooting agent with **no skills and no multi-step workflow**. It runs a single LangGraph **ReAct loop**: the LLM reasons, calls Splunk Observability MCP tools when it needs data, observes the results, and repeats until it produces an answer.

The goal is not perfection. You are establishing what the agent does **without playbooks** so you can compare against Part 2 (skills) and Part 3 (structured graph).

## Baseline Agent

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

Make sure you completed [Configure Environment]({{< ref "5-configure-agent-environment" >}}) — virtual environment installed, `.env` configured, and both doctor commands passing.

Start with a CLI investigation using the workshop defaults — service **`payment`**, environment **`sre-agent-workshop`**:

{{< tabs >}}
{{% tab title="Script" open="true" %}}

```bash
cd ~/troubleshooting-agent
source .venv/bin/activate
cd part1_agent
troubleshooting-agent chat "Why does payment have errors in the sre-agent-workshop environment?"
```

{{% /tab %}}
{{% tab title="Example Output" %}}

```text
(.venv) splunk@ip-172-31-19-27:~/troubleshooting-agent/part1_agent$ troubleshooting-agent chat "Why does payment have errors in the sre-agent-workshop environment?"
INFO Splunk OTel initialized service=troubleshooting-agent
INFO HTTP Request: POST https://lite-llm-proxy.splunko11y.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO [inv=chat:5a4dffc6d704] Log file: /home/splunk/troubleshooting-agent/shared/logs/investigations/chat-5a4dffc6d704.jsonl
INFO [inv=chat:5a4dffc6d704] 
INFO [inv=chat:5a4dffc6d704] ══════════════════════════════════════════════════════════════
INFO [inv=chat:5a4dffc6d704]  Investigation  chat:5a4dffc6d704  |  part1_agent  |  cli
INFO [inv=chat:5a4dffc6d704] ──────────────────────────────────────────────────────────────
INFO [inv=chat:5a4dffc6d704]  Query: Why does payment have errors in the sre-agent-workshop environment?
INFO [inv=chat:5a4dffc6d704]  LLM: openai  |  MCP tools available: 12
INFO [inv=chat:5a4dffc6d704] ══════════════════════════════════════════════════════════════
INFO HTTP Request: GET https://api.multitenant.galileocloud.io/healthcheck "HTTP/1.1 200 OK"
INFO HTTP Request: POST https://api.multitenant.galileocloud.io/login/api_key "HTTP/1.1 200 OK"
INFO HTTP Request: GET https://api.multitenant.galileocloud.io/current_user "HTTP/1.1 200 OK"
INFO HTTP Request: GET https://api.multitenant.galileocloud.io/projects?project_name=sre-agent-wkshp-shw-2cb1&type=gen_ai "HTTP/1.1 200 OK"
INFO HTTP Request: POST https://api.multitenant.galileocloud.io/projects "HTTP/1.1 200 OK"
INFO HTTP Request: GET https://api.multitenant.galileocloud.io/projects/26a65ecc-5b04-43b8-adf0-4aabf5af4b94/log_streams/paginated?include_counts=false&starting_token=0&limit=500 "HTTP/1.1 200 OK"
INFO HTTP Request: POST https://api.multitenant.galileocloud.io/projects/26a65ecc-5b04-43b8-adf0-4aabf5af4b94/log_streams "HTTP/1.1 200 OK"
INFO HTTP Request: GET https://api.multitenant.galileocloud.io/ingest/healthz "HTTP/1.1 200 OK"
INFO HTTP Request: POST https://api.multitenant.galileocloud.io/v2/projects/26a65ecc-5b04-43b8-adf0-4aabf5af4b94/sessions/search "HTTP/1.1 200 OK"
INFO HTTP Request: POST https://api.multitenant.galileocloud.io/v2/projects/26a65ecc-5b04-43b8-adf0-4aabf5af4b94/sessions "HTTP/1.1 200 OK"
INFO Galileo session=chat-5a4dffc6d704 | part1_agent project=sre-agent-wkshp-shw-2cb1 stream=sre-agent-wkshp console=https://console.multitenant.galileocloud.io
INFO HTTP Request: POST https://lite-llm-proxy.splunko11y.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO [inv=chat:5a4dffc6d704]  trace_id=963b3abe6a9c149c418f84c5fea67a82 [1] LLM turn 1 — calling tools: o11y_search_alerts_or_incidents
INFO [inv=chat:5a4dffc6d704]  trace_id=963b3abe6a9c149c418f84c5fea67a82 [2] MCP o11y_search_alerts_or_incidents — OK
INFO HTTP Request: POST https://lite-llm-proxy.splunko11y.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO [inv=chat:5a4dffc6d704]  trace_id=963b3abe6a9c149c418f84c5fea67a82 [2] LLM turn 2 — calling tools: o11y_get_apm_service_errors_and_requests
INFO [inv=chat:5a4dffc6d704]  trace_id=963b3abe6a9c149c418f84c5fea67a82 [3] MCP o11y_get_apm_service_errors_and_requests — OK
INFO HTTP Request: POST https://lite-llm-proxy.splunko11y.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO [inv=chat:5a4dffc6d704]  trace_id=963b3abe6a9c149c418f84c5fea67a82 [3] LLM turn 3 — composing final response
INFO HTTP Request: POST https://api.multitenant.galileocloud.io/ingest/traces/26a65ecc-5b04-43b8-adf0-4aabf5af4b94 "HTTP/1.1 200 OK"
INFO [inv=chat:5a4dffc6d704] ──────────────────────────────────────────────────────────────
INFO [inv=chat:5a4dffc6d704]  Done — 3 LLM turns | 2 tool calls | 18.2s
INFO [inv=chat:5a4dffc6d704]  Log file: /home/splunk/troubleshooting-agent/shared/logs/investigations/chat-5a4dffc6d704.jsonl
INFO [inv=chat:5a4dffc6d704] ══════════════════════════════════════════════════════════════
INFO [inv=chat:5a4dffc6d704] 
INFO [inv=chat:5a4dffc6d704] ──────────────────────────────────────────────────────────────
INFO [inv=chat:5a4dffc6d704]  Agent response
INFO [inv=chat:5a4dffc6d704] ──────────────────────────────────────────────────────────────
INFO [inv=chat:5a4dffc6d704] payment in sre-agent-workshop shows elevated errors in the last hour. I found … (summary from MCP tool JSON — your run may differ)
INFO [inv=chat:5a4dffc6d704] ══════════════════════════════════════════════════════════════
```

{{% /tab %}}
{{< /tabs >}}

You can also paste alert text from the facilitator's demo. Always include **service** (`payment`) and **environment** (`sre-agent-workshop`) when asking about a specific service.

## Read the terminal trace

With `AGENT_LOG_TRACE=true` (the default), every run prints a structured trace to the terminal. As you read it, ask:

1. **Which MCP tools did the agent call?** — Look for `[n] MCP o11y_...` lines.
2. **Which tools did it skip?** — A baseline agent often skips traces, logs, or infrastructure correlation.
3. **Were parameters correct?** — Service should be `payment`, environment `sre-agent-workshop` (exact APM names). Time ranges should use `{"start": "-1h", "stop": "now"}` inside a `params` object.
4. **Is the answer grounded?** — Does the final response reflect actual JSON from tool results, or does it sound plausible without evidence?

The same events are written to `shared/logs/investigations/<id>.jsonl` for post-workshop review. Each run prints the path at the end (look for `Log file:` in the output).

{{< notice title="Tip" style="tip" >}}
Cleared your terminal before you could review the trace? You have two easy options:

- **Open the JSONL log** — use the `Log file:` path from the end of the run, or list the newest file:
  ```bash
  ls -t ~/troubleshooting-agent/shared/logs/investigations/*.jsonl | head -1
  ```
- **Re-run the same command** — run `troubleshooting-agent chat "Why does payment have errors in the sre-agent-workshop environment?"` again. You will get a new trace (and a new Galileo session), but the investigation flow is the same.
{{< /notice >}}

## Review the run in Galileo

After your chat completes, open the **Galileo console** and navigate to:

1. **Project** — the name you set (for example, `sre-agent-wkshp-shw-2cb1`)
2. **Agent Stream** — your log stream from `.env` (for example, `sre-agent-wkshp`)
3. **Sessions** — find the most recent session (named `chat-9265e3375c8b | part1_agent`)

Select the session to open the trace view. You should see three areas: the **trace tree** on the left, the **chat** in the center (user query and agent response), and detail tabs on the right.

Expand the trace tree. A typical Part 1 run looks like this:

```text
Agent
├── Agent:agent          ← LLM turn
├── should_continue      ← graph routing
├── tools
│   └── o11y_get_apm_service_errors_and_requests   ← MCP tool (names vary by run)
├── Agent:agent          ← next LLM turn
└── should_continue
```

Click **`tools`** and the nested MCP span to inspect arguments and JSON responses. Compare what Galileo captured with what the terminal trace showed — they should tell the same story.

{{< diagram src="images/part1-galileo-trace.png" alt="Galileo Agent Stream showing a Part 1 session with trace tree, chat, and Evaluators tab" caption="A Part 1 session in Agent Stream — trace tree on the left, conversation in the center. Evaluator scores appear after you enable them in the next section." width="960" >}}

{{< notice title="Tip" style="tip" >}}
Keep the Galileo console open in a browser tab during the workshop. After each investigation, refresh and locate your session — it is the fastest way to compare Part 1, Part 2, and Part 3 on the same alert.
{{< /notice >}}

## Baseline exercise

Work through this checklist using the workshop defaults — **`payment`** in environment **`sre-agent-workshop`**:

| Step | Action |
|------|--------|
| 1 | Run `troubleshooting-agent chat "Why does payment have errors in the sre-agent-workshop environment?"` |
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

**Next:** [Part 2 — Skill Playbooks]({{< ref "8-part2-skill-playbooks" >}}) — see how keyword-injected skills change investigation quality and Galileo traces.
