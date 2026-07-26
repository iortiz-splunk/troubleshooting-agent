# Troubleshooting Agent Workshop

AI troubleshooting agent for applications and systems. This repo is organized as a **three-part workshop**: shared integrations (MCP, Slack, LLM, observability) plus three agent implementations of increasing capability.

**Workshop instructions:** [https://iortiz-splunk.github.io/troubleshooting-agent/](https://iortiz-splunk.github.io/troubleshooting-agent/)

## Prerequisites

- Python 3.11+
- An LLM: **Ollama**, **OpenAI-compatible** API, or **Azure OpenAI**
- Node.js `npx` when Splunk MCP integrations are enabled

Configure credentials and integrations first — see **[shared/README.md](shared/README.md)**.

## Install

**Workshop participants** — fast install with pinned dependencies (no dev tools):

```bash
cd troubleshooting-agent
cp .env.example .env   # edit with your keys — see shared/README.md
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-workshop.txt
pip install -e . --no-deps
```

**Contributors** — editable install with dev and observability extras:

```bash
pip install -e ".[dev,observability]"
```

## Workshop parts

Same CLI everywhere — **`troubleshooting-agent`** — behavior depends on **which directory you run it from**:

| Part | Directory | What you get |
|------|-----------|--------------|
| **1** | `part1_agent/` | Minimal MCP-only agent |
| **2** | `part2_agent/` | Agent + 3 skill playbooks (manual wiring) |
| **3** | `part3_agent/` | Full agent + troubleshoot orchestration skill |

### Quick commands

```bash
cd part1_agent
troubleshooting-agent doctor
troubleshooting-agent chat "Why is Verification slow?"
troubleshooting-agent slack-listen

cd ../part2_agent
troubleshooting-agent chat "Investigate latency on Verification"

cd ../part3_agent
troubleshooting-agent slack-listen
```

From the repo root you can override with `--part part3_agent` (optional).

## MCP load test (facilitators)

Stress-test Splunk MCP capacity before a large workshop — simulates concurrent Part 3 participants **without an LLM** (scripted MCP tool calls only). Supports up to **200** participants; use a dedicated EC2 instance for large runs.

**Quick steps:**

```bash
# 1. Install (from repo root, after main workshop install)
source .venv/bin/activate
pip install -e ".[loadtest]"

# 2. Verify MCP (same .env as the workshop)
cd part3_agent && troubleshooting-agent mcp-doctor && cd ..

# 3a. UI — laptop / small runs (1–50 participants typical)
streamlit run tools/mcp_load_runner/app.py
# → Run MCP preflight in sidebar → set participants → Start load test

# 3b. CLI — EC2 / large runs (recommended for 50+)
ulimit -n 65535
mcp-load-test preflight --servers o11y
mcp-load-test run -n 200 --servers o11y --ramp-up 120 --output-json results.json
```

Full sizing, EC2 instance recommendations, and how to read results: **[tools/mcp_load_runner/README.md](tools/mcp_load_runner/README.md)**.

## Project layout

```text
shared/workshop_shared/   # MCP, Slack, LLM, config, unified CLI
part1_agent/              # Part 1: agent.py, prompt.py
part2_agent/              # Part 2: + skills/ (3 playbooks)
part3_agent/              # Part 3: + skill_router.py, skills/
tools/mcp_load_runner/    # MCP load test (Streamlit UI + mcp-load-test CLI)
tests/
```

## Development

```bash
pytest tests -q
ruff check shared part1_agent part2_agent part3_agent tests
```

## Documentation

Participant-facing workshop instructions: **[https://iortiz-splunk.github.io/troubleshooting-agent/](https://iortiz-splunk.github.io/troubleshooting-agent/)**

To preview locally (requires [Hugo Extended](https://gohugo.io/installation/)):

```bash
cd docs
hugo server -D --config hugo.toml,config/local.toml
```

Open http://localhost:1313/

### Publishing the site

The site deploys automatically from the **`workshop`** branch via GitHub Actions (see [`.github/workflows/hugo-pages.yml`](.github/workflows/hugo-pages.yml)). In repo **Settings → Environments → github-pages**, allow the **`workshop`** branch under **Deployment branches and tags** (or choose **All branches**).

- **[shared/README.md](shared/README.md)** — LLM, Splunk MCP, Slack, Galileo, OTel setup
- **[part1_agent/README.md](part1_agent/README.md)** — baseline exercise
- **[part2_agent/README.md](part2_agent/README.md)** — skill wiring exercises
- **[part3_agent/README.md](part3_agent/README.md)** — facilitator demo script
- **[tools/mcp_load_runner/README.md](tools/mcp_load_runner/README.md)** — MCP capacity / load testing
