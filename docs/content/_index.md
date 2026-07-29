---
title: "Troubleshooting Agent Workshop"
description: "Build and instrument an AI troubleshooting agent with LangChain, MCP, and OpenTelemetry."
weight: 1
duration: "90 minutes"
---

In this hands-on workshop you will build a **troubleshooting agent** that investigates real observability alerts — the same kind of workflow SRE and platform teams run every day, now powered by an LLM with structured tool access.

**Learning Objectives:**

- Give the agent **playbooks** (skills) that guide investigation steps instead of leaving every decision to the model
- Progress from a minimal ReAct loop to a **multi-node LangGraph workflow** with identify → categorize → investigate → report stages
- Use **Splunk Agent Observability** to monitor what the agent does during an investigation — trace tool calls, follow reasoning steps, and see how it moves through each workflow node
- Evaluate agent outputs for **hallucinations**, **factual accuracy**, and whether conclusions are grounded in data returned by tools
- Assess **tool selection** and decision quality — did the agent choose the right observability queries and investigation path for the alert at hand?

## What you'll build

The repo contains **three progressive agent implementations** that share the same CLI and integrations. Each part adds capability on top of the last:

| Part | Focus | Agent shape |
|------|-------|-------------|
| **Part 1** | Baseline MCP-only agent | Single ReAct loop — tools only, no playbooks |
| **Part 2** | Skill playbooks | Same ReAct loop + keyword-injected `SKILL.md` playbooks |
| **Part 3** | Production-style workflow | Four-node LangGraph graph + full skill library |

All three parts use the same command — `troubleshooting-agent` — from their respective directories. Shared integrations (LLM, MCP, observability) live in `shared/workshop_shared/` and are pre-built for you.

## Prerequisites

You need access to your workshop instance (see [Connect to EC2]({{< ref "3-connect-ec2" >}})). The repository and credentials are already set up on the instance — complete [Configure Environment]({{< ref "5-configure-agent-environment" >}}) before Part 1.

## Getting started

The repository is at `~/troubleshooting-agent` on your instance. Follow the workshop steps in order:

1. [Connect to EC2]({{< ref "3-connect-ec2" >}})
2. [Deploy the OpenTelemetry Collector]({{< ref "4-deploy-otel-collector" >}})
3. [Configure Environment]({{< ref "5-configure-agent-environment" >}})
4. [Part 1 — Baseline Agent]({{< ref "6-part1-baseline-agent" >}})
5. [Configure Galileo Log Stream Evaluators]({{< ref "7-galileo-logstream-evaluators" >}})
6. [Part 2 — Skill Playbooks]({{< ref "8-part2-skill-playbooks" >}})
7. [Part 3 — Full Workflow]({{< ref "9-part3-full-workflow" >}})
8. [Production-Ready Agent]({{< ref "10-production-ready-agent" >}}) *(optional)*

## Workshop flow

The workshop is organized into setup steps and three agent parts:

0. **Setup** — Connect to EC2, deploy the OTel collector, configure Galileo, verify doctors
1. **Part 1 — Baseline agent** — Run the minimal MCP-only agent. Observe what it finds without playbooks.
2. **Galileo evaluators** — Enable log stream evaluators to score tool selection, grounding, and hallucination risk.
3. **Part 2 — Skill playbooks** — Run keyword-injected skills, author the error-rate playbook, compare Galileo evaluators.
4. **Part 3 — Full workflow** — Explore the four-node LangGraph graph; see skills load **per workflow step** (different from Part 2's upfront router).
5. **Production-ready agent** *(optional)* — Hardening checklist for live incident use after the workshop.

## Key concepts

**MCP tools** — The agent calls Splunk Observability and Splunk Cloud through MCP rather than hard-coded API clients. Tools like `o11y_get_apm_service_latency` and `splunk_run_query` appear in the agent's tool list at runtime.

**Skills (playbooks)** — Markdown files with YAML frontmatter that describe when to use a playbook, which tools to call, and how to interpret results. Skills turn open-ended LLM reasoning into repeatable investigation steps. See the [AI Skills]({{< ref "2-ai-skills" >}}) section for why they matter, how to create them, and repo examples.

**Structured traces** — With `AGENT_LOG_TRACE=true` (the default), every investigation prints numbered steps, tool calls, and a final response block to the terminal. JSONL trace files are also written to `shared/logs/investigations/` for post-run review.

{{< notice title="Tips" style="tip" >}}
- Run commands from the **part directory** (`part1_agent/`, `part2_agent/`, `part3_agent/`) — the CLI picks up the agent for that part automatically.
- Workshop demo defaults: service **`payment`**, environment **`sre-agent-workshop`** — include both in chat prompts during Parts 1 and 2.
- Use `troubleshooting-agent chat "your question"` for investigations during the workshop.
- If a tool call fails, check `troubleshooting-agent mcp-doctor` first — most issues are credential or gateway configuration.
- Compare Part 1 and Part 3 responses on the **same alert** to see the impact of skills and graph structure.
{{< /notice >}}
