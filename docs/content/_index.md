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

Before starting, make sure you have:

- **Python 3.11+** and **Node.js** with `npx` (for Splunk MCP)
- An EC2 instance from the workshop (see [Connect to EC2](/troubleshooting-agent/3-connect-ec2/))
- Workshop credentials exported as **EC2 environment variables** (LLM, Splunk MCP, Galileo API — provided by facilitators)

Copy `.env.example` to `.env` and add your personal Galileo project and log stream names. Follow [Configure Agent Environment](/troubleshooting-agent/5-configure-agent-environment/) to install Python dependencies, configure `.env`, and verify connectivity before Part 1.

## Getting started

The repository should already be on your EC2 instance at `~/troubleshooting-agent`. Clone it yourself only if your facilitator instructs you to:

```bash
git clone https://github.com/iortiz-splunk/troubleshooting-agent.git
cd troubleshooting-agent
```

Python setup, `.env` configuration, and doctor checks are covered in [Configure Agent Environment](/troubleshooting-agent/5-configure-agent-environment/) — complete that section before Part 1.

## Workshop flow

The workshop is organized into setup steps and three agent parts:

0. **Setup** — Connect to EC2, deploy the OTel collector, configure Galileo, verify doctors
1. **Part 1 — Baseline agent** — Run the minimal MCP-only agent. Observe what it finds without playbooks.
2. **Part 2 — Skill playbooks** — See how keyword-injected skills change investigation quality.
3. **Part 3 — Full workflow** — Explore the four-node LangGraph graph and full skill library.

## Key concepts

**MCP tools** — The agent calls Splunk Observability and Splunk Cloud through MCP rather than hard-coded API clients. Tools like `o11y_get_apm_service_latency` and `splunk_run_query` appear in the agent's tool list at runtime.

**Skills (playbooks)** — Markdown files with YAML frontmatter that describe when to use a playbook, which tools to call, and how to interpret results. Skills turn open-ended LLM reasoning into repeatable investigation steps. See the [AI Skills](/troubleshooting-agent/2-ai-skills/) section for why they matter, how to create them, and repo examples.

**Structured traces** — With `AGENT_LOG_TRACE=true` (the default), every investigation prints numbered steps, tool calls, and a final response block to the terminal. JSONL trace files are also written to `shared/logs/investigations/` for post-run review.

{{< notice title="Tips" style="tip" >}}
- Run commands from the **part directory** (`part1_agent/`, `part2_agent/`, `part3_agent/`) — the CLI picks up the agent for that part automatically.
- Use `troubleshooting-agent chat "your question"` for investigations during the workshop.
- If a tool call fails, check `troubleshooting-agent mcp-doctor` first — most issues are credential or gateway configuration.
- Compare Part 1 and Part 3 responses on the **same alert** to see the impact of skills and graph structure.
{{< /notice >}}
