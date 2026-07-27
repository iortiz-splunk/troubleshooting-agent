---
title: "Configure Galileo Log Stream Evaluators"
description: "Enable Galileo evaluators on your log stream to score agent responses, tool selection, hallucination risk, and investigation quality."
weight: 7
navTitle: "Galileo Evaluators"
duration: "15 minutes"
---

You already send agent traces to Galileo from Part 1. In this section you turn on **log stream evaluators** so Galileo automatically scores each investigation — not just records it.

Evaluators answer questions that are hard to judge by eye across dozens of runs:

- Did the agent pick the **right MCP tools** for the alert?
- Did tool calls **fail** because of bad parameters?
- Is the final answer **grounded in tool output**, or does it sound plausible without evidence?
- Did the agent **complete** the investigation goal, or stop early?


## Before you start

| Requirement | Why |
|-------------|-----|
| [Part 1 investigation completed](/troubleshooting-agent/6-part1-baseline-agent/) | We will use the session/trace from the previous section to compare the before and after enabling evaluators |
| `.env` Galileo settings saved | Same `GALILEO_PROJECT` and `GALILEO_LOG_STREAM` you used in Part 1 |
| Galileo console access | Open the project your facilitator shared (or the one you created with `GALILEO_PROJECT`) |

Most out-of-the-box evaluators use an **SLM** (Galileo Luna) or **LLM-as-a-judge** to score traces. Prefer **SLM** when configuring evaluators. Your workshop instance should already have an LLM integration configured in Galileo. If evaluator scores stay empty after several minutes, ask your facilitator to verify **Integrations** in the Galileo console.

## Open your log stream

1. Sign in to the Galileo console.
2. Open **Projects** and select your project (for example, `sre-agent-wkshp-shw-2cb1`).
3. Select **Agent Stream** in the sidebar — this is the log stream named in your `.env` (for example, `sre-agent-wkshp`).
4. Confirm you see at least one session from Part 1 (for example, `chat-9265e3375c8b | part1_agent`).

## Configure evaluators

1. From the log stream view, click **Configure Evaluators**.
2. Search or filter the evaluator list.
3. Turn on the evaluators in the tables below.
4. When Galileo offers a choice between **LLM** and **SLM** (Luna), select **SLM** — same scoring intent, with lower latency and cost during the workshop.
5. Click **Apply** to save your evaluator selections. Toggles alone do not take effect until you apply.
6. When Agent Observability asks whether to compute evaluators on **past logs**, click **Not Now**. Your Part 1 session stays as the **without evaluators** baseline; you will run a fresh investigation next so you can compare both traces side by side.

{{< notice title="Why Not Now?" style="tip" >}}
Keep your first Part 1 session un-scored on purpose. After you re-run the same chat command, you will have two sessions in the same log stream: one **trace only** (Part 1) and one **trace + evaluator scores** (this section). That makes the before/after difference easy to see.
{{< /notice >}}
{{< notice title="Prefer SLM when available" style="tip" >}}
Many built-in evaluators have an **SLM** variant powered by Galileo Luna models. Use SLM for workshop runs unless your facilitator asks you to compare against the full LLM judge. If you do not see an SLM option for an evaluator, the LLM variant is fine.
{{< /notice >}}

## Recommended evaluators

Enable evaluators from **two categories** that map directly to troubleshooting-agent quality. Not every evaluator applies to every span type — Galileo only scores where the node type matches.

### Agent behavior — tools and progress

Use these to score **how the agent investigates**, not just what it says at the end.

| Evaluator | Node type | What it tells you | Workshop focus |
|-----------|-----------|-------------------|----------------|
| [**Tool selection quality**](https://docs.galileo.ai/concepts/metrics/agentic/tool-selection-quality) | LLM span | Whether the model chose appropriate tools for the task | Did it call `o11y_get_apm_service_errors_and_requests` vs. skipping straight to a vague answer? |
| [**Tool error**](https://docs.galileo.ai/concepts/metrics/agentic/tool-error) | Tool span | Failures during tool execution | Catches MCP validation errors (for example, missing `environment_name`) |
| [**Action advancement**](https://docs.galileo.ai/concepts/metrics/agentic/action-advancement) | Trace | Whether each step moves the investigation forward | Useful when comparing shallow Part 1 runs vs. deeper Part 2/3 runs |
| [**Action completion**](https://docs.galileo.ai/concepts/metrics/agentic/action-completion) | Session | Whether the agent achieved the user's goal | Did it actually investigate errors, or only ask clarifying questions? |
| [**Agent efficiency**](https://docs.galileo.ai/concepts/metrics/agentic/agent-efficiency) | Session | Whether the path to the answer was reasonably direct | Flags excessive LLM turns or redundant tool calls |
| [**Reasoning coherence**](https://docs.galileo.ai/concepts/metrics/agentic/reasoning-coherence) | LLM span | Logical consistency across planning steps | More useful in Part 3's multi-node graph |

**Minimum set for Part 1:** turn on **Tool selection quality**, **Tool error**, and **Action completion**.

### Response quality — hallucination and grounding

These evaluators judge the **final answer** against the evidence available in the trace.

| Evaluator | Node type | What it tells you | Workshop focus |
|-----------|-----------|-------------------|----------------|
| [**Context adherence**](https://docs.galileo.ai/concepts/metrics/rag/generation-quality/context-adherence) | LLM span | Closed-domain hallucination — claims not supported by provided context | Scores low when the model invents service names, error rates, or root causes not present in MCP JSON |
| [**Correctness**](https://docs.galileo.ai/concepts/metrics/response-quality/correctness) | LLM span | Factual accuracy of the response | Complements context adherence when tool output is sparse |
| [**Instruction adherence**](https://docs.galileo.ai/concepts/metrics/response-quality/instruction-adherence) | LLM span | Whether the model followed system instructions | Part 1's prompt requires using `o11y_*` tools for live data |
| [**Completeness**](https://docs.galileo.ai/concepts/metrics/rag/generation-quality/completeness) | LLM span | Whether the answer addresses all parts of the user query | Flags partial answers when the user asked about errors, latency, and dependencies |

**Minimum set for hallucination checks:** turn on **Context adherence** and **Instruction adherence**.

{{< notice title="Context adherence vs. correctness" style="tip" >}}
**Context adherence** is the primary hallucination signal for this workshop: it checks whether claims appear in the **context Galileo sees** (tool outputs attached to the trace). **Correctness** is broader factuality and is most useful when you have a known-good answer or rich tool results to compare against.
{{< /notice >}}

After you click **Apply**, reopen **Configure Evaluators** to confirm your selections. It should look similar to this:

{{< diagram src="images/evaluators-selection.png" alt="Galileo Configure Evaluators pane with workshop evaluators enabled" >}}



## Exercise — score your baseline run

After you apply evaluators and click **Not Now** on past logs, re-run the same Part 1 investigation. You will end up with two sessions in your log stream: your original Part 1 run (trace only) and this new run (trace + evaluator scores).

### Run the investigation

Re-run Part 1 with the **same service** and include the **workshop environment** in your prompt. Without an environment name, MCP tools often fail validation on the first call — the agent may stop after asking for clarification instead of investigating.

Use the environment your facilitator provides (for example, `splunk-hipster`):

{{< tabs >}}
{{% tab title="Script" open="true" %}}

```bash
cd ~/troubleshooting-agent
source .venv/bin/activate
cd part1_agent
troubleshooting-agent chat "Why does paymentservice have errors in the splunk-hipster environment?"
```

{{% /tab %}}
{{< /tabs >}}

You can also paste alert text from the facilitator's demo or substitute a different service or environment if instructed.


### Review the run in Galileo

After your chat completes, open the **Galileo console** and navigate to:

1. **Project** — the name you set (for example, `sre-agent-wkshp-shw-2cb1`)
2. **Agent Stream** — your log stream from `.env` (for example, `sre-agent-wkshp`)
3. **Sessions** — use the session picker (for example, **Session 2 of 2**) to find your two Part 1 runs: the original (trace only) and the newest (with evaluator scores)

Select the **newest** session. When the environment is in the prompt, the trace tree often shows **multiple tool rounds** — the agent is trying, even if the final answer is still incomplete:

```text
Agent (~16s)
├── Agent:agent
│   ├── should_continue
│   └── tools
│       └── o11y_search_alerts_or_incidents
├── Agent:agent
│   ├── should_continue
│   └── tools
│       └── o11y_get_apm_service_errors_and_requests
├── Agent:agent
│   └── should_continue
```

If the environment is missing, you may see a **shallower** trace instead — for example a single call to `o11y_get_apm_environments` and a response asking you to specify the environment.

The center panel shows the **chat** — your query and the agent's final response. On the right, open the **Evaluators** tab to see scores grouped under headings such as **Agent Quality**. SLM evaluators are labeled with **(SLM)**, for example:

- **Action Advancement (SLM)** — did each step move the investigation forward?
- **Action Completion (SLM)** — did the agent finish the job, or stop at summaries and "next steps"?
- **Agent Efficiency** — was the path reasonably direct? (may show **System error** if Galileo cannot score that run — ask your facilitator)

Click into each **`tools`** span to inspect MCP inputs, outputs, and span-level evaluators. Use the **chat** panel and **Evaluators** tab together — a detailed-sounding answer can still score low if the agent did not complete the investigation.

{{< diagram src="images/part1-galileo-trace-with-env.png" alt="Galileo Agent Stream showing a deeper Part 1 run with multiple MCP tools and low evaluator scores" caption="With the environment in the prompt, the agent calls alert search and APM error tools — but Action Completion (SLM) can still be 1% when the answer stops at suggested next steps instead of a root cause." width="960" >}}

Work through this checklist with the investigation prompt your facilitator provides (errors on **paymentservice** in your workshop environment is the default):

1. Run `troubleshooting-agent chat` with the **service and environment** in the query (see command above).
2. Open Galileo **Agent Stream** — find **both** sessions using the session picker (for example, **Session 2 of 3** for the scored re-run).
3. On the **newest** session, expand the trace tree — confirm multiple **`tools`** spans ran (not just a single environment lookup).
4. Click each MCP span — do the numbers and facts in the **chat** response match the tool JSON?
5. Open the **Evaluators** tab and record scores under **Agent Quality** (and other groups if present).
6. **Compare** your sessions — the Part 1 baseline (trace only) vs. this run (trace + evaluator scores).
7. **Save your notes and scores** — you will re-run the same scenario in Part 2 and Part 3.

{{< tabs >}}
{{% tab title="What good looks like" %}}

A strong Part 1 run (for a data-rich environment) might show:

- **Tool selection quality** — high; tools align with APM errors, traces, or dependencies
- **Tool error** — high (no failures)
- **Context adherence** — high; conclusions cite numbers and service names from MCP JSON
- **Action completion** — moderate to high; a clear root-cause summary, not just suggested next steps

A shallow run (missing environment) is still useful baseline data:

- Single tool call such as `o11y_get_apm_environments`, then the agent **asks for environment**
- **Action Completion (SLM)** — **0%**; the investigation never started

A deeper run that **still scores low** is common in Part 1 — the screenshot above is a real example:

- Prompt includes environment; agent calls `o11y_search_alerts_or_incidents` and `o11y_get_apm_service_errors_and_requests`
- Chat cites real numbers (for example, ~398 errors out of 1250 requests) — looks productive at first glance
- **Action Completion (SLM)** and **Action Advancement (SLM)** — still **1%** because the agent stops at a summary and offers "next steps" instead of finishing the investigation
- **Agent Efficiency** — may show **System error**; ask your facilitator if an evaluator fails to score

Other weak patterns to watch for:

- **Tool selection quality** — low; model answered without calling tools
- **Context adherence** — low; detailed root cause with empty or failed tool output

{{% /tab %}}
{{% tab title="When scores are missing" %}}

If evaluator scores do not appear:

1. Confirm you ran a **new** investigation after saving evaluator settings
2. Check **Configure Evaluators** — the evaluator toggle is still on and you clicked **Apply**
3. Verify sampling is **100%** under **Evaluator Sampling** in the same pane
4. Ask your facilitator to confirm the Galileo **LLM integration** is configured

{{% /tab %}}
{{< /tabs >}}

{{< notice title="Tip" style="tip" >}}
Part 1 intentionally has **no playbook**, so results can range from weak to strong across runs and even between participants. A response can **sound detailed** in the chat panel but still score poorly on **Action Completion** — evaluators help you see that gap without reading every tool JSON by hand.
{{< /notice >}}

## What you learned

- Log streams **capture** traces; **evaluators** score them automatically on each session after you enable them.
- Clicking **Not Now** on past logs keeps a clean **before/after** pair of sessions to compare.
- **Agentic evaluators** (tool selection, tool error, action completion) measure investigation behavior.
- **Response quality evaluators** (context adherence, instruction adherence) surface **hallucination** and prompt-following gaps.
- Baseline **Part 1 scores** become your ruler when you add skills (Part 2) and graph structure (Part 3) on the same alert.

---

**Next:** Part 2 — Skill Playbooks (coming soon) — re-run the same investigation and compare evaluator scores after playbooks guide tool selection.
