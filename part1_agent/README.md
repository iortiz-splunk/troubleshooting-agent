# Part 1 — Minimal agent

**Prerequisite:** integrations configured → [shared/README.md](../shared/README.md)

## What to read

| File | Purpose |
|------|---------|
| `agent.py` | LangGraph ReAct loop + `run_chat` |
| `prompt.py` | MCP-only system prompt |

Part 1 uses **MCP tools only** (no built-in stubs, no skills).

## Run

```bash
cd part1_agent
troubleshooting-agent doctor
troubleshooting-agent mcp-doctor
troubleshooting-agent chat "Why is Verification slow?"
troubleshooting-agent slack-listen
```

Terminal output is structured by default (`AGENT_LOG_TRACE=true`) — see [shared/README.md](../shared/README.md#what-you-see-in-the-terminal). JSONL trace files land in `shared/logs/investigations/`.

## Exercise

1. Trigger an Observability alert in Slack (or paste alert text into `chat`).
2. Observe baseline investigation — note what the agent fetches vs. skips.
3. Compare with Part 3 after the facilitator demo.
