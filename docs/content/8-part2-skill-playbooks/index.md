---
title: "Part 2 — Skill Playbooks"
description: "Run the skill-injected ReAct agent, compare Galileo traces and evaluators to Part 1, and author your own error-rate playbook."
weight: 8
navTitle: "Part 2 — Skill Playbooks"
duration: "30 minutes"
---

Part 2 uses the **same ReAct loop as Part 1**, but adds **playbooks** — markdown skills that tell the agent which MCP tools to call, in what order, and how to format the answer. You will run the facilitator demo, see what changes in **Galileo**, then complete your own **`error-rate`** skill and run the agent again.

For background on why skills matter, see [AI Skills]({{< ref "2-ai-skills" >}}). This section focuses on **doing** Part 2.

## Part 1 vs Part 2 — agent differences

| Component | Part 1 | Part 2 |
|-----------|--------|--------|
| **Agent loop** | LangGraph ReAct | Same ReAct loop |
| **Playbooks** | None | One **domain** skill + always-on **`investigation-report`** |
| **Routing** | — | Keyword match on your chat/alert text (`alert_signals` in frontmatter) |
| **Galileo session** | `chat-… \| part1_agent` | `chat-… \| part2_agent` |
| **Extra Galileo trace** | — | **`skill_router`** — all skills injected **before** the ReAct loop |

```text
Your message → keyword router → SKILL.md → system prompt → ReAct loop (LLM + MCP tools)
```

| File | Purpose |
|------|---------|
| `part2_agent/agent.py` | Builds prompt with injected skills; logs routing metadata |
| `part2_agent/skill_inject.py` | Keyword router and prompt assembly |
| `part2_agent/skills/` | Playbook library — you edit skills here |
| `part2_agent/skills/_template/SKILL.md` | Blank template for new playbooks |

## Run the facilitator demo

Make sure [Part 1]({{< ref "6-part1-baseline-agent" >}}) and [Galileo Evaluators]({{< ref "7-galileo-logstream-evaluators" >}}) are done — you will compare against those sessions.

From `part2_agent`, run a **latency** investigation. Use the workshop defaults — service **`payment`**, environment **`sre-agent-workshop`**:

{{< tabs >}}
{{% tab title="Script" open="true" %}}

```bash
cd ~/troubleshooting-agent
source .venv/bin/activate
cd part2_agent
troubleshooting-agent chat "Investigate latency on payment in the sre-agent-workshop environment"
```

{{% /tab %}}
{{< /tabs >}}

The keyword router should select **`latency-spike`** because the message contains signals like `latency`. The agent should also load **`investigation-report`** on every Part 2 run (report formatting — not matched by keywords).

{{< notice title="Workshop defaults" style="tip" >}}
Use **`payment`** and **`sre-agent-workshop`** for all Part 2 chat commands unless your facilitator says otherwise — same service and environment as Part 1.
{{< /notice >}}

## Review Part 2 in Galileo

Open **Agent Stream** and find the newest session named `chat-… | part2_agent`.

{{< notice title="Skills are prompt injection, not MCP tools" style="primary" >}}
Playbooks are appended to the **system prompt** before the ReAct loop runs. You will **not** see `load_skill:investigation-report` or `load_skill:latency-spike` under **`Agent` → `tools`** — those spans only show MCP calls like `o11y_search_alerts_or_incidents`.

To confirm skills loaded, check:
1. **Terminal** — lines like `[N] Skill loaded: latency-spike` and `[N] Skill loaded: investigation-report`
2. **Galileo** — a separate **`skill_router`** trace in the same session (sibling to **`Agent`**, not nested inside it)
3. **Chat JSON** — the system message includes `## Active playbook` and `## Reporting requirements`
{{< /notice >}}

### skill_router trace

Part 2 logs a **`skill_router`** trace **before** the main **`Agent`** trace in the same session. In the session trace list, select **`skill_router`** (it is not a child of **`Agent`**):

```text
Session: chat-… | part2_agent
├── skill_router                    ← select this trace first
│   ├── load_skill:latency-spike      ← domain playbook (keyword match)
│   └── load_skill:investigation-report   ← always-on report format
└── Agent                           ← ReAct loop (MCP tools appear here)
    ├── Agent::Agent
    ├── tools → o11y_…
    └── …
```

Click each **`load_skill:*`** span to see how many characters of that playbook were added to the system prompt.

### Main investigation trace

The ReAct trace looks like Part 1 (`Agent:agent`, `tools`, `should_continue`), but tool order should follow the active playbook — for **`latency-spike`**, expect:

1. `o11y_search_alerts_or_incidents`
2. `o11y_get_apm_service_latency`

Even when alert search returns an empty list, the agent **must** still call step 2 (`o11y_get_apm_service_latency` or error metrics) and format the final reply using **`investigation-report`** headings — not stop after one tool or ask "would you like me to pull metrics?"

The **`latency-spike`** playbook and system prompt tell the agent to omit `severity` unless you asked for it (wrong type causes MCP validation errors) and to treat empty alerts as normal for CLI runs.

### Compare evaluators to Part 1

On the **Evaluators** tab, compare this session to your Part 1 baseline on a similar alert:

| Evaluator | What to look for |
|-----------|------------------|
| **Tool selection quality** | Did the agent call the tools the playbook names? |
| **Action advancement / completion** | Did it get further than Part 1’s “please provide environment” or “here are next steps” stops? |
| **Context adherence** | Are cited metrics present in MCP tool output? |
| **Instruction adherence** | Did it follow the report skill (no raw JSON dumps)? |

Scores may still be low in Part 2 — that is useful data. The goal is to see **whether skills change behavior and scores**, not to hit 100% yet.

{{< notice title="Tip" style="tip" >}}
Filter Agent Stream by session name suffix **`part2_agent`**, or use the session picker to compare **`part1_agent`** vs **`part2_agent`** runs side by side.
{{< /notice >}}

## Anatomy of a SKILL.md

Every playbook lives in `part2_agent/skills/<skill-name>/SKILL.md`. Open **`skills/latency-spike/SKILL.md`** as the reference while you work.

### YAML frontmatter (routing + metadata)

The file starts with YAML between `---` lines:

| Field | Purpose |
|-------|---------|
| **`name`** | Skill identifier (usually matches the folder name) |
| **`description`** | One line — when to use this playbook |
| **`alert_signals`** | Keywords matched against your chat/alert text (lowercase) |
| **`mcp_tools`** | Tools the playbook expects — guides the model and facilitators |
| **`rule_patterns`** | Optional — document detector name patterns (reference only in Part 2) |

Example from **`latency-spike`**:

```yaml
---
name: latency-spike
description: Investigate APM latency alerts using o11y_get_apm_service_latency.
alert_signals:
  - latency
  - duration
  - p99
  - slow
mcp_tools:
  - o11y_search_alerts_or_incidents
  - o11y_get_apm_service_latency
---
```

### Markdown body (the playbook)

| Section | Purpose |
|---------|---------|
| **When to use** | Symptoms or alert types that match |
| **Tool sequence** | Ordered MCP steps with parameter hints (`service_name`, `environment_name`, `time_range`) |
| **Interpretation** | How to read the metrics — not just what to call |
| **Do not** | Guardrails (wrong params, skipping steps, inventing data) |

Part 2 also loads **`investigation-report`** automatically — it is not selected by keywords. It defines the **final answer format** for every run.

{{< notice title="Important" style="primary" >}}
Tool names must match **`mcp-doctor`** exactly (`o11y_*` prefix). Time ranges belong inside a **`params`** object: `{"start": "-1h", "stop": "now"}`.
{{< /notice >}}

For a blank starting point, copy `skills/_template/SKILL.md`. More examples live in [AI Skills]({{< ref "2-ai-skills" >}}).

## Lab — complete the error-rate skill

Your task: finish the starter stub at **`part2_agent/skills/error-rate/SKILL.md`** so the router picks **`error-rate`** when the user mentions errors or 5xx.

Work from **`latency-spike/SKILL.md`** — same structure, different tools and signals.

Before you pick tools, review what the MCP servers expose. Your instance should match **`troubleshooting-agent mcp-doctor`** (see [Configure Environment]({{< ref "5-configure-agent-environment" >}})). **Bold** tools are the ones the error-rate lab expects; the rest are available if you extend your playbook.

{{< collapse title="Splunk Observability MCP tools (o11y_*) — click to expand" >}}
| Tool | What it's for |
|------|----------------|
| **`o11y_search_alerts_or_incidents`** | Find active or recent alerts and incidents by service, environment, detector, or keywords — capture `eventId` when present |
| **`o11y_get_apm_service_errors_and_requests`** | Error count and request volume time series for one service — primary metric tool for error-rate investigations |
| `o11y_get_apm_service_latency` | Latency percentiles (p50/p90/p99) for a service — used by the latency-spike playbook |
| `o11y_get_apm_services` | Aggregate request, error, and latency metrics across services — useful for traffic or health comparisons |
| `o11y_get_apm_service_dependencies` | Upstream and downstream APM dependencies for a service |
| `o11y_get_apm_exemplar_traces` | Sample trace IDs linked to latency buckets or errors — deeper drill-down (Part 3) |
| `o11y_get_apm_trace_tool` | Full trace detail for a specific `trace_id` |
| `o11y_get_apm_environments` | List APM environment names when the user did not specify one |
| `o11y_get_metric_names` | Discover metric names available for SignalFlow queries |
| `o11y_get_metric_metadata` | Units and dimensions for a named metric |
| `o11y_generate_signalflow_program` | Build a SignalFlow program from a natural-language description |
| `o11y_execute_signalflow_program` | Run SignalFlow and return metric time series |
{{< /collapse >}}

{{< collapse title="Splunk Cloud MCP tools (splunk_*) — Part 3 preview" >}}
| Tool | What it's for |
|------|----------------|
| `splunk_run_query` | Run read-only SPL against Splunk Cloud — primary log search (required in Part 3 before concluding) |
| `splunk_get_indexes` | List indexes and storage tiers — use when the log index is unknown |
| `splunk_get_metadata` | Field names, event types, and sources for an index — narrows SPL before searching |
| `splunk_get_info` | Splunk instance version and identity — connectivity checks |

Part 2 playbooks focus on **`o11y_*`** tools. Log search skills use **`splunk_*`** in Part 3.
{{< /collapse >}}

1. Open **`skills/error-rate/SKILL.md`** in your editor.
2. **Frontmatter** — replace the `TODO` entries:
   - **`description`** — one line: investigate error-rate / 5xx alerts using APM error metrics
   - **`alert_signals`** — include `error`, `errors`, and `5xx` (add others if useful)
   - **`mcp_tools`** — list `o11y_search_alerts_or_incidents` and `o11y_get_apm_service_errors_and_requests`
3. **When to use** — when the alert or user message mentions elevated errors or error rate.
4. **Tool sequence** — two steps:
   - Search alerts / incidents — capture `eventId` when present; **if empty, continue to step 2**
   - Get APM service errors and requests — **required**; `service_name`, `environment_name`, `time_range` in `params`
5. **Interpretation** — at least two bullets (for example: error count vs request volume; errors spiking with traffic vs independently).
6. **Do not** — at least one rule (for example: do not state root cause without metric evidence from tools).
7. Save the file.

{{< notice title="Check your routing" style="tip" >}}
The router counts how many **`alert_signals`** appear in your message. A prompt with **`5xx`** or **`errors`** should score **`error-rate`** higher than **`latency-spike`**.
{{< /notice >}}

## Run Part 2 with your skill

After saving **`error-rate/SKILL.md`**, run an error-focused investigation:

{{< tabs >}}
{{% tab title="Script" open="true" %}}

```bash
cd ~/troubleshooting-agent/part2_agent
troubleshooting-agent chat "Investigate elevated 5xx errors on payment in the sre-agent-workshop environment"
```

{{% /tab %}}
{{< /tabs >}}

### Confirm in Galileo

1. Open the new **`part2_agent`** session in Agent Stream.
2. Expand **`skill_router`** — expect **`load_skill:error-rate`** and **`load_skill:investigation-report`**.
3. Expand the main trace — expect at least **`o11y_search_alerts_or_incidents`** and **`o11y_get_apm_service_errors_and_requests`** under **`tools`** spans.
4. Open **Evaluators** — compare scores to your Part 1 and latency-demo Part 2 sessions.

Work through this checklist:

1. **`skill_router`** shows **`error-rate`** as the domain skill.
2. The trace includes **two or more** MCP tool calls aligned with your playbook.
3. The **chat** response cites **interpreted** numbers from tool output (not generic advice).
4. The reply uses **`investigation-report`** headings — no raw JSON blocks.
5. **Evaluator scores** are recorded — note which improved vs Part 1.

{{< notice title="Tip" style="tip" >}}
If the wrong skill loads, check **`alert_signals`** spelling and re-run with clearer keywords (`5xx`, `errors`, `error rate`) in the prompt.
{{< /notice >}}

## What you learned

- Part 2 is still a **single ReAct loop** — skills change the **system prompt**, not the graph shape.
- **`alert_signals`** drive keyword routing; **`investigation-report`** always loads for consistent handoffs.
- Galileo **`skill_router`** makes injection visible — you can audit which playbook ran.
- Authoring a skill means defining **signals, tool order, interpretation, and guardrails** — not new Python code.
- Evaluators help quantify whether skills improved **tool selection** and **completion** vs the Part 1 baseline.

## Intentional gaps (Part 3 preview)

Part 2 deliberately stops short of a full production workflow:

| Capability | Part 2 | Part 3 |
|------------|--------|--------|
| Graph | Single ReAct | Four nodes: identify → categorize → investigate → report |
| Skills per run | One domain + report | Product skill + log search + full report |
| Exemplar traces | Not in playbooks | Yes |
| Alert anchoring | Keyword routing | Strict detector / incident matching |
| Skill timing in Galileo | **`skill_router`** trace, then **`Agent`** | **`load_skill:*`** under each graph node — see [Part 3]({{< ref "9-part3-full-workflow" >}}) |

---

**Next:** [Part 3 — Full Workflow]({{< ref "9-part3-full-workflow" >}}) — same alert through a structured LangGraph pipeline; skills load **per step**, not upfront like Part 2.
