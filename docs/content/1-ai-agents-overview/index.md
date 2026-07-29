---
title: "Overview of AI Agents"
description: "A high-level look at the core components of an AI agent — orchestration, models, tools, and observability."
weight: 1
navTitle: "Overview of AI Agents"
---

Before building a troubleshooting agent, it helps to see how the pieces fit together. An AI agent is not just a chat model — it is a **system** that combines reasoning, action, and feedback loops. The diagram below shows the main components and how data flows between them during a typical investigation.

{{< diagram src="images/ai-agent-components.png" alt="High-level diagram of AI agent components: AI models, skills, MCP servers, tools, vector databases, and Splunk Agent Observability and guardrails" caption="Core components of an AI agent and how they interact during a run." width="960" >}}

## Review the Agent Orchestration Layer

The **agent** is the orchestrator. It accepts a goal (for example, *“investigate this latency alert”*), decides what to do next, calls tools when it needs data, and produces a final answer. Unlike a single prompt/response chat, an agent runs in a **loop**: plan → act → observe → repeat until the task is done or a limit is reached.

Common patterns you will encounter:

| Pattern | What it does | Example in this workshop |
|---------|--------------|--------------------------|
| **ReAct** | Reason about the task, then call a tool, then reason again from the result | Part 1 and Part 2 agents |
| **Graph / workflow** | Fixed stages with specialized nodes (identify, investigate, report) | Part 3 LangGraph workflow |
| **Tool routing** | Choose which capability to invoke based on context | Skill injection in Part 2; product routing in Part 3 |

**Frameworks** provide the scaffolding for these patterns so you do not wire loops, state, and tool calls from scratch:

- **[LangChain](https://www.langchain.com/)** — Chains, agents, tool bindings, and LLM integrations. Good for composing prompts, tools, and memory in Python (and other languages).
- **[LangGraph](https://www.langchain.com/langgraph)** — State machines and multi-step graphs on top of LangChain. Used when you need explicit stages, branching, and durable workflow state (Part 3).
- **Other ecosystems** — CrewAI, AutoGen, and vendor SDKs follow similar ideas: an orchestration layer, a model, and callable tools. Concepts transfer even if APIs differ.

In this workshop the agent code lives in `part1_agent/`, `part2_agent/`, and `part3_agent/` — each directory is a different orchestration design built on the same shared integrations.

## Review the AI Model as the Reasoning Engine

The **model** (LLM) is the reasoning engine. It interprets alerts and user messages, chooses which tool to call (when the framework allows it), and synthesizes natural-language conclusions from tool output. It does **not** directly query Splunk or Observability unless you give it tools to do so — the model proposes actions; the agent runtime executes them.

Models differ in capability, cost, latency, and context window size. In production you often:

- Use a **stronger model** for complex reasoning or final reports
- Use a **faster or local model** (e.g. Ollama) for iterative development
- Swap providers via configuration without rewriting agent logic — this workshop supports Ollama, OpenAI-compatible APIs, and Azure OpenAI through `shared/workshop_shared/llm/`

{{< notice title="Important" style="primary" >}}
Models can **hallucinate** — state plausible but incorrect facts. That is why tool grounding (real metrics, logs, alert JSON) and observability (below) are essential for agent systems you trust in operations.
{{< /notice >}}

## Explore MCP Tools Available to the Agent

**Tools** extend the agent beyond text generation. Each tool is a callable function with a name, description, and input schema. The model reads those descriptions and the runtime invokes the tool when the agent decides it needs external data or action.

Common categories:

| Type | Purpose | Examples |
|------|---------|----------|
| **Data retrieval** | Fetch live state from systems | APM latency, error rates, Splunk search results |
| **Search & discovery** | Find relevant entities | List services, search alerts/incidents, look up indexes |
| **Action** | Change state (use carefully) | Acknowledge incident, post message, run remediation |
| **Utility** | Support reasoning | Load a skill playbook, format a report, parse JSON |

Tools can be implemented as native Python functions or exposed through **MCP (Model Context Protocol)** — a standard way for agents to discover and call capabilities hosted by external servers. In this workshop, Splunk Observability and Splunk Cloud capabilities arrive as MCP tools (prefixed `o11y_`, `splunk_`, etc.) so the agent sees a unified tool list at runtime.

Good tool design drives good agent behavior:

- **Clear names and descriptions** — the model chooses tools based on what it reads
- **Structured inputs/outputs** — JSON beats free-form text for reliability
- **Least privilege** — expose only what the agent needs for the task

**Skills (playbooks)** in Parts 2 and 3 are not tools themselves — they are guidance injected into the agent’s context so it follows a consistent investigation sequence when using tools.

## Monitor Agent Runs with Splunk Agent Observability

Running an agent without observability is like running a microservice with no traces: you see the final response but not **how** the system got there. **Splunk Agent Observability** (and complementary signals such as structured terminal traces and OpenTelemetry) let you monitor agent runs in production and during development.

What to monitor:

| Signal | Why it matters |
|--------|----------------|
| **Traces / spans** | See each step: LLM calls, tool invocations, graph node transitions |
| **Tool calls** | Which APIs ran, with what inputs, and what came back |
| **Decisions** | Route taken (e.g. APM vs logs), skills loaded, retries |
| **Quality** | Hallucinations, accuracy vs ground truth, completeness of investigation |
| **Latency & cost** | Time per step, tokens used, tool round-trips |

This workshop emphasizes evaluating agents along those dimensions: you will compare Part 1 and Part 3 on the same alert, inspect tool selection, and verify conclusions against real observability data rather than trusting the model’s prose alone.

Structured traces (`AGENT_LOG_TRACE=true`) give immediate feedback in the terminal; Splunk Agent Observability provides session-level views for deeper analysis across many runs — essential when agents move from demo to something operators rely on.

---

**Next:** [AI Skills]({{< ref "2-ai-skills" >}}) — why playbooks matter, how to author `SKILL.md` files, and examples from this repo.
