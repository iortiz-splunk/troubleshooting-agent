# Part 2 — Skills (manual wiring)

**Prerequisite:** [shared/README.md](../shared/README.md)

Everything you need is in this folder: `agent.py`, `prompt.py`, and `skills/`.

## Skills (not auto-loaded)

| Skill | File |
|-------|------|
| Alert triage | `skills/alert-triage/SKILL.md` |
| Latency spike | `skills/latency-spike/SKILL.md` |
| Error rate | `skills/error-rate/SKILL.md` |

Part 2 **does not** inject skills at runtime. Use Cursor to wire playbook steps into `prompt.py`.

## Run

```bash
cd part2_agent
troubleshooting-agent chat "Investigate latency on Verification"
troubleshooting-agent slack-listen
```

## Exercises

1. Open `skills/latency-spike/SKILL.md` in Cursor — ask it to add the tool sequence to `prompt.py`.
2. Trigger a latency alert; compare before/after in Galileo traces.
3. Draft a new playbook for an alert type Part 2 does not cover (homework).

Part 3 adds more skills in its own `skills/` folder — not available here.
