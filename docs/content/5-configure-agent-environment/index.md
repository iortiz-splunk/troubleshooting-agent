---
title: "Configure Agent Environment"
description: "Install dependencies, personalize your Galileo settings, and verify everything is ready before Part 1."
weight: 5
navTitle: "Configure Agent Environment"
duration: "10 minutes"
---

Your workshop instance and credentials are already configured. Before Part 1, you will **install the agent dependencies** and **personalize your Galileo project name** so you can find your traces during the workshop.

## Install dependencies

From the repo on your instance:

{{< tabs >}}
{{% tab title="Script" open="true" %}}

```bash
cd ~/troubleshooting-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-workshop.txt
pip install -e . --no-deps
```

{{% /tab %}}
{{% tab title="Example Output" %}}

```text
Successfully installed langchain-1.3.14 galileo-2.5.1 ...
Successfully installed troubleshooting-agent-0.1.0
```

{{% /tab %}}
{{< /tabs >}}

{{< notice title="Tip" style="tip" >}}
Run `source .venv/bin/activate` whenever you open a new SSH session. Your prompt should show `(.venv)` when the environment is active.
{{< /notice >}}

## Personalize your Galileo settings

Create your `.env` file and set a **unique Galileo project name** so your agent runs are easy to find:

```bash
cd ~/troubleshooting-agent
cp .env.example .env
nano .env
```

Add or update these lines (use your instance name from `echo $INSTANCE` — see [Connect to EC2](/troubleshooting-agent/3-connect-ec2/)):

```bash
ENABLE_GALILEO=true
GALILEO_PROJECT="sre-agent-wkshp-$INSTANCE"
GALILEO_LOG_STREAM="sre-agent-wkshp"
```

For example, if `echo $INSTANCE` prints `shw-2cb1`:

```bash
GALILEO_PROJECT="sre-agent-wkshp-shw-2cb1"
GALILEO_LOG_STREAM="sre-agent-wkshp"
```

{{< notice title="Tip" style="tip" >}}
Use the same `GALILEO_PROJECT` across Parts 1–3 so all your investigations appear in one place.
{{< /notice >}}

Save and exit (`Ctrl + O`, `Enter`, `Ctrl + X` in nano). Your file should look similar to this:

{{< diagram src="images/env-example.png" alt="Example .env file with ENABLE_GALILEO and personalized Galileo project name" >}}

## Splunk Agent Observability with Galileo

**Galileo** captures each agent investigation as a trace you can review in the browser:

- Each **LLM turn** — what the model decided to do next
- Each **tool call** — which MCP tools ran, with inputs and outputs
- **Token usage** — input, output, and total tokens for the session

| Signal | Where | Best for |
|--------|-------|----------|
| **Terminal trace** | CLI output during a run | Live narration |
| **JSONL files** | `shared/logs/investigations/` | Review after a run |
| **Galileo sessions** | Galileo console | Comparing runs across Parts 1–3 |

In **Part 1**, traces show a simple **ReAct loop** — the model alternates between an `agent` node (reasoning) and a `tools` node (MCP calls). Parts 2 and 3 add skills and named workflow nodes.

Each investigation creates a **session** named like `chat:abc123 | part1_agent` in your Galileo project.

## Verify setup

With your virtual environment activated and `.env` saved, run:

{{< tabs >}}
{{% tab title="Script" open="true" %}}

```bash
cd ~/troubleshooting-agent
source .venv/bin/activate
cd part1_agent
troubleshooting-agent doctor
troubleshooting-agent mcp-doctor
```

{{% /tab %}}
{{% tab title="Example Output" %}}

```text
$ troubleshooting-agent doctor
OK  LLM provider=openai  model=gpt-4.1-mini

$ troubleshooting-agent mcp-doctor
OK  Splunk Observability MCP connected
    Tools available: 12
    Sample: o11y_search_alerts_or_incidents, o11y_get_apm_service_latency, ...
```

{{% /tab %}}
{{< /tabs >}}

{{< notice title="Important" style="primary" >}}
Both commands should report **OK** before you continue. If either fails, ask your facilitator for help.
{{< /notice >}}

---

**Next:** [Part 1 — Baseline Agent](/troubleshooting-agent/6-part1-baseline-agent/) — run your first investigation and review traces in the terminal and Galileo.
