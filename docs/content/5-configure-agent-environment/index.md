---
title: "Configure Agent Environment"
description: "Install Python dependencies, create your .env file, set Galileo project and log stream, then verify LLM and Splunk Observability MCP connectivity before Part 1."
weight: 5
navTitle: "Configure Agent Environment"
duration: "15 minutes"
---

Workshop credentials are injected as **EC2 environment variables** by facilitators. You still create a local `.env` file, but only for settings that are **unique to you** (mainly Galileo project and log stream names).

The agent loads configuration through Pydantic Settings: it reads your `.env` file **and** picks up variables already exported in your shell. When the same variable exists in both places, **the EC2 environment variable wins**.

**Prerequisites:** Ubuntu EC2 instance from [Connect to EC2](/troubleshooting-agent/3-connect-ec2/), repo at `~/troubleshooting-agent`, **Python 3.10+** (`python3 --version`), and **Node.js** with `npx` (required for Splunk MCP).

## Install Python dependencies

Pull the latest workshop branch, then create a virtual environment and install from the **pinned requirements file**. This avoids pip's dependency resolver, which can backtrack for 30+ minutes if you use the `dev` extra.

{{< notice title="Tip" style="tip" >}}
If SSH might disconnect during install, run inside `tmux` or `screen` so the install continues in the background: `tmux new -s install`
{{< /notice >}}

{{< tabs >}}
{{% tab title="Script" open="true" %}}

```bash
cd ~/troubleshooting-agent
git pull origin workshop
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
pip install -r requirements-workshop.txt
pip install -e . --no-deps
```

{{% /tab %}}
{{% tab title="Example Output" %}}

```text
Successfully installed langchain-1.3.14 galileo-2.5.1 rpds-py-0.30.0 ...
Successfully installed troubleshooting-agent-0.1.0
```

{{% /tab %}}
{{< /tabs >}}

| Step | What it does |
|------|----------------|
| `pip install -r requirements-workshop.txt` | Installs pinned third-party packages (LangChain, Galileo, OTel, etc.) |
| `pip install -e . --no-deps` | Registers this repo and the `troubleshooting-agent` CLI without re-resolving dependencies |

{{< notice title="Important" style="primary" >}}
Do **not** use `pip install -e ".[dev,observability]"` during the workshop. The `dev` extra pulls in **ruff**, **mypy**, and **pytest** — tools you do not need to run the agent.
{{< /notice >}}

{{< notice title="Tip" style="tip" >}}
Run `source .venv/bin/activate` whenever you open a new SSH session before using `troubleshooting-agent`. Your shell prompt should show `(.venv)` when the environment is active. Run `deactivate` to leave the virtual environment.
{{< /notice >}}

If a previous install failed partway, start fresh:

```bash
cd ~/troubleshooting-agent
git pull origin workshop
deactivate 2>/dev/null || true
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
pip install -r requirements-workshop.txt
pip install -e . --no-deps
```

## Create your .env file

From the repo root (with your virtual environment activated):

```bash
cd ~/troubleshooting-agent
cp .env.example .env
nano .env
```

You do **not** need to fill in every line in `.env.example`. Leave workshop credential lines blank or commented out — the agent reads those from EC2 environment variables instead.

### Pre-set on EC2 (do not add to .env)

Facilitators export these on your instance. The agent picks them up automatically:

| Variables | Purpose |
|-----------|---------|
| `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL_NAME` | LLM (OpenAI-compatible proxy) |
| `ENABLE_SPLUNK_O11Y`, `SPLUNK_O11Y_*` | Splunk Observability MCP (`o11y_*` tools) |
| `ENABLE_SPLUNK_CLOUD_MCP`, `SPLUNK_CLOUD_MCP_*` | Splunk Cloud / logs MCP |
| `ENABLE_SPLUNK_OTEL`, `OTEL_*`, `SPLUNK_ACCESS_TOKEN` | OTel APM for the agent process |
| `GALILEO_API_KEY`, `GALILEO_CONSOLE_URL` | Galileo API access |

`LLM_PROVIDER` is optional — when `OPENAI_API_KEY` and `OPENAI_BASE_URL` are set from EC2, the agent auto-selects the OpenAI-compatible provider.

### What you add to .env

Add only the settings below — these are **not** pre-set on EC2:

```bash
# Enable Galileo tracing (API key and console URL come from EC2 env)
ENABLE_GALILEO=true
GALILEO_PROJECT="sre-agent-wkshp-$INSTANCE"
GALILEO_LOG_STREAM="sre-agent-wkshp"
```

Replace `$INSTANCE` with the value from `echo $INSTANCE` (from [Connect to EC2](/troubleshooting-agent/3-connect-ec2/)). For example, if `echo $INSTANCE` prints `shw-2cb1`:

```bash
GALILEO_PROJECT="sre-agent-wkshp-shw-2cb1"
GALILEO_LOG_STREAM="sre-agent-wkshp"
```

{{< notice title="Tip" style="tip" >}}
Use the same `GALILEO_PROJECT` across Parts 1–3 so all investigations appear together. Change only `GALILEO_LOG_STREAM` if you want to separate runs by part.
{{< /notice >}}

Save and exit the editor (`Ctrl + O`, `Enter`, `Ctrl + X` in nano).

At the end, your `.env` should look something like this:

{{< diagram src="images/env-example.png" alt="Example of .env file with ENABLE_GALILEO and personalized Galileo project name" >}}

{{< notice title="Important" style="primary" >}}
Do not commit `.env` to git. Your file should contain only your Galileo names — not shared API keys.
{{< /notice >}}

## Splunk Agent Observability with Galileo

**Galileo** is the agent observability platform used in this workshop. Every investigation you run sends a **trace** to Galileo showing:

- Each **LLM turn** — what the model decided to do next
- Each **tool call** — which MCP tools ran, with inputs and outputs
- **Token usage** — input, output, and total tokens for the session

This complements what you see in the terminal:

| Signal | Where | Best for |
|--------|-------|----------|
| **Terminal trace** | CLI output (`AGENT_LOG_TRACE=true`, default) | Live narration during a run |
| **JSONL files** | `shared/logs/investigations/` | Logs of each agent session |
| **Galileo sessions** | Galileo console (`GALILEO_CONSOLE_URL` on your instance) | Persistent traces, comparing runs, sharing with your team |

In **Part 1**, Galileo traces show a simple **ReAct loop** — the model alternates between an `agent` node (reasoning) and a `tools` node (MCP calls) until it produces a final answer. Parts 2 and 3 add skill metadata; Part 3 adds named workflow nodes (`identify`, `investigate`, `report`, etc.).

Each investigation creates a **session** in your Galileo project and log stream. CLI runs are named like `chat:abc123 | part1_agent` so you can find your trace after each `troubleshooting-agent chat` command.

## Verify connectivity

With the virtual environment **activated** and your `.env` in place, confirm the LLM and Splunk Observability MCP integrations are working:

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
Both commands must report **OK** before continuing. If `mcp-doctor` fails, the agent has no live Observability data and may hallucinate conclusions.
{{< /notice >}}

If either command fails, ask your facilitator — EC2 environment variables should already supply the LLM and MCP credentials.

---

**Next:** [Part 1 — Baseline Agent](/troubleshooting-agent/6-part1-baseline-agent/) — run your first investigation and review traces in the terminal and Galileo.
