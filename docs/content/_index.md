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

{{< notice title="Tips" style="tip" >}}
- Run commands from the **part directory** (`part1_agent/`, `part2_agent/`, `part3_agent/`) — the CLI picks up the agent for that part automatically.
- Workshop demo defaults: service **`payment`**, environment **`sre-agent-workshop`** — include both in chat prompts during Parts 1 and 2.
- Use `troubleshooting-agent chat "your question"` for investigations during the workshop.
- If a tool call fails, check `troubleshooting-agent mcp-doctor` first — most issues are credential or gateway configuration.
- Compare Part 1 and Part 3 responses on the **same alert** to see the impact of skills and graph structure.
{{< /notice >}}
