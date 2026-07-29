---
title: "Part 3 — Full Workflow"
description: "Run the four-node LangGraph agent, compare how skills load per workflow step in Galileo, and contrast with Part 2's upfront keyword router."
weight: 9
navTitle: "Part 3 — Full Workflow"
duration: "30 minutes"
---

Part 3 replaces the single ReAct loop with a **four-node LangGraph workflow**: **identify → categorize → investigate → report**. The same `SKILL.md` playbook format from Part 2 applies — but **when and where** skills load in Galileo looks different on purpose.

Complete [Part 2 — Skill Playbooks]({{< ref "8-part2-skill-playbooks" >}}) first so you have a baseline for keyword injection and the upfront **`skill_router`** trace.

## Part 2 vs Part 3 — how skills load in Galileo

Both parts inject playbooks into the **system prompt** — skills are not MCP tools. The difference is **timing and orchestration**.

| | Part 2 | Part 3 |
|---|--------|--------|
| **Orchestration** | Single ReAct loop (same as Part 1) | Four-node graph — each step has its own prompt |
| **Skill selection** | Keyword router on your chat/alert text | Python categorizer on the alert payload (APM / IM / RUM / Synthetics) |
| **When skills load** | **All at once**, before the agent's first LLM turn | **One step at a time**, when that graph node runs |
| **Galileo trace shape** | Separate **`skill_router`** trace, then **`Agent`** | **`load_skill:*`** spans **inside** each node (`identify`, `investigate`, `report`) |
| **Skills per run** | One domain skill + always-on `investigation-report` | Different skills per phase — see table below |

{{< notice title="Don't expect skill_router in Part 3" style="primary" >}}
If you just finished Part 2, you may look for a top-level **`skill_router`** block with every playbook listed upfront. **Part 3 does not use that pattern.** Skills appear under the node that needs them — that is the production-style workflow the workshop is teaching.
{{< /notice >}}

### Part 2 trace (what you saw in Part 2)

Skills load **before** the ReAct loop starts. Galileo shows a sibling trace:

```text
Session: chat-… | part2_agent
├── skill_router                         ← all playbooks injected here
│   ├── load_skill:latency-spike
│   └── load_skill:investigation-report
└── Agent                                ← MCP tools only appear here
    ├── Agent::Agent
    ├── tools → o11y_search_alerts_or_incidents
    └── …
```

### Part 3 trace (what to look for instead)

Skills load **when each node runs**. Look for **`load_skill:*`** spans nested under named workflow nodes:

```text
Session: chat-… | part3_agent
└── part3_investigation
    ├── identify
    │   ├── load_skill:get-alerts-or-incidents   ← step 1 playbook
    │   ├── identify_llm
    │   └── identify_tools → o11y_…
    ├── categorize
    │   └── load_skill:troubleshoot-apm-incidents   ← routing decision (example)
    ├── investigate
    │   ├── load_skill:troubleshoot-apm-incidents   ← product playbook
    │   ├── load_skill:search-logs                  ← mandatory log search
    │   ├── investigate_llm
    │   └── investigate_tools → o11y_… / splunk_…
    └── report
        ├── load_skill:troubleshoot-report          ← final report format
        └── report_llm
```

Same skill files (`SKILL.md`), different **orchestration layer**:

- **Part 2** teaches *authoring* playbooks with a simple keyword router.
- **Part 3** teaches *orchestrating* playbooks — load the right runbook at the right workflow step.

## Skills loaded at each node

| Node | Skill(s) loaded | Why here |
|------|-----------------|----------|
| **identify** | `get-alerts-or-incidents` | Confirm the alert and capture IDs before investigating |
| **categorize** | *(routing only)* | Code picks product type — no full playbook yet |
| **investigate** | Product skill (e.g. `troubleshoot-apm-incidents`) + **`search-logs`** | Product-specific MCP steps + mandatory Splunk log search |
| **report** | `troubleshoot-report` | Structured handoff — only after evidence is gathered |

The investigate node also injects **`search-logs/indexes.md`** — a catalog of Splunk indexes for the workshop tenant so the agent searches the right index instead of defaulting to `main`.

## Run Part 3

Participants run Part 3 from the CLI with a **mock Observability alert** — no Slack integration required. The prompt includes service, environment, **`detectorId`**, and rule name so the **identify** node can anchor the investigation like a real alert thread.

From `part3_agent`:

{{< tabs >}}
{{% tab title="Script" open="true" %}}

```bash
cd ~/troubleshooting-agent
source .venv/bin/activate
cd part3_agent
troubleshooting-agent chat "Troubleshoot the Splunk Observability alert: payment service in sre-agent-workshop environment. DetectorId HNcv52_AwAA. Rule: SRE Agent - PaymentService High Error Rate. Find root cause of the high error rate and confirm whether it is resolved."
```

{{% /tab %}}
{{< /tabs >}}

{{< notice title="Mock alert fields" style="tip" >}}
The workshop prompt mirrors a Slack alert: **service** (`payment`), **environment** (`sre-agent-workshop`), **detector ID**, and **rule name**. Part 3 uses these to fetch the alert payload, categorize as APM, run **`troubleshoot-apm-incidents`** + **`search-logs`**, then format **`troubleshoot-report`**.
{{< /notice >}}

Galileo sessions are named `chat-… | part3_agent`. Expect **`part3_investigation`** with nodes **`identify` → `categorize` → `investigate` → `report`** — not a single ReAct **`Agent`** trace.

## Review Part 3 in Galileo

1. Open **Agent Stream** and find a session ending in **`part3_agent`**.
2. Expand **`part3_investigation`** — confirm **named nodes** (`identify`, `categorize`, `investigate`, `report`), not repeated generic `Agent:Agent` spans.
3. Under **`identify`**, **`investigate`**, and **`report`**, expand **`load_skill:*`** spans — note **when** each playbook enters the prompt relative to MCP tool calls.
4. Compare to your Part 2 session on a similar alert — same tools may run, but the trace **shape** and **skill timing** should differ.

{{< notice title="Tip" style="tip" >}}
Side-by-side comparison: Part 2 loads **`investigation-report`** at the start with the domain skill. Part 3 loads **`troubleshoot-report`** only in the **report** node — after investigate has gathered evidence.
{{< /notice >}}

## What you learned

- Part 3 uses the same **`SKILL.md`** format as Part 2 — orchestration changed, not the playbook file shape.
- **Part 2** = keyword router, all skills upfront, visible in **`skill_router`**.
- **Part 3** = graph nodes, skills per step, visible as **`load_skill:*`** under each node.
- Production agents often look more like Part 3: workflow engine decides *when* to attach each runbook.

For skill authoring details and the full Part 3 skill library, see [AI Skills]({{< ref "2-ai-skills" >}}).

**Next:** [Production-Ready Agent]({{< ref "10-production-ready-agent" >}}) — what to harden after the workshop before running on live incidents.
