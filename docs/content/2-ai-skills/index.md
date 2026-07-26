---
title: "AI Skills"
description: "Why playbooks matter, how to author SKILL.md files, and how skills are loaded in Parts 2 and 3 of the workshop."
weight: 2
navTitle: "AI Skills"
---

An **AI skill** (also called a **playbook**) is a markdown file that tells the agent *how* to investigate — which tools to call, in what order, with which parameters, and what guardrails to follow. Skills do not replace tools; they **guide** the model so investigations are repeatable, grounded, and safe.

In this workshop, every skill lives under `skills/<skill-name>/SKILL.md` with optional companion files such as `reference.md` or `indexes.md`.

## Review Why Skills Matter for Agent Investigations

Without skills, the agent has tools and a general system prompt — but every run is an open-ended reasoning problem. The model must rediscover your runbook each time: which MCP tool to call first, how to format `params.time_range`, when to search logs, and when to stop. That leads to inconsistent quality, wasted tool calls, and conclusions that sound plausible but skip critical steps.

Skills address those gaps by encoding **operational knowledge** the model does not reliably infer on its own:

| Problem without skills | What skills provide |
|------------------------|---------------------|
| Skips log search after APM metrics | Explicit **workflow order** (metrics → traces → logs → report) |
| Wrong MCP parameters (`latency` instead of `lat_buck_`) | **Parameter literals** and do-not rules |
| Searches wrong Splunk index (`main` vs workshop index) | **Environment catalog** (`indexes.md`) scoped to your tenant |
| Invents facts when tools return nothing | **Guardrails** — state “no data found,” do not fabricate |
| Different answer every run on the same alert | **Repeatable playbooks** facilitators can review and improve |

Skills are especially valuable in **production agent systems** because they:

- **Reduce hallucination risk** — the agent is steered toward tool output, not free-form guessing.
- **Capture tribal knowledge** — senior SRE runbooks become version-controlled artifacts, not chat prompts.
- **Improve observability** — when a skill is loaded, traces show *which playbook* ran, making debugging and evaluation easier.
- **Enable safe iteration** — you can tighten one playbook without rewriting the whole agent.

In Part 1 you see the baseline: tools only. Parts 2 and 3 show how the same tools behave differently when playbooks are injected at the right time.

## Distinguish Skills, Tools, and Prompts

Keep these roles separate when you design an agent:

| Layer | Role | Example in this workshop |
|-------|------|---------------------------|
| **System prompt** | Global behavior, tone, safety | Base instructions in `prompt.py` |
| **Tools (MCP)** | Fetch or act on external systems | `o11y_get_apm_service_latency`, `splunk_run_query` |
| **Skills** | Task-specific investigation steps | `troubleshoot-apm-incidents`, `search-logs` |

The model **chooses** tools (within what the framework exposes). Skills **constrain and sequence** that choice so the investigation matches your standards.

## Review How Skills Load in Parts 2 and 3

Loading differs by part — same file format, different orchestration:

| Part | Mechanism | When skills load |
|------|-----------|------------------|
| **Part 2** | Keyword router in `skill_inject.py` | One **domain** skill + `investigation-report`, matched from alert/user text via `alert_signals` |
| **Part 3** | LangGraph nodes in `graph.py` + `skill_tools.py` | **Identify:** `get-alerts-or-incidents` · **Investigate:** product skill (APM/IM/RUM/Synthetics) + mandatory **`search-logs`** · **Report:** `troubleshoot-report` |

Part 3 also injects the **log index catalog** (`search-logs/indexes.md`) into the investigate prompt so the agent searches the correct Splunk index before probing the cluster.

## Create a New Skill Playbook

### Create the Skill Directory

Each skill is a folder under the part’s `skills/` tree:

```text
part2_agent/skills/
  your-skill-name/
    SKILL.md          # required
    reference.md      # optional — extra field names, links, tables
```

For Part 3, add skills under `part3_agent/skills/` and wire them in the graph or router if they should load automatically.

### Add YAML Frontmatter to SKILL.md

Every `SKILL.md` starts with YAML between `---` delimiters. At minimum:

```yaml
---
name: your-skill-name
description: One line — when the agent should use this playbook
---
```

**Part 2** skills often include routing metadata:

```yaml
alert_signals:
  - latency
  - slow
  - p99
mcp_tools:
  - o11y_search_alerts_or_incidents
  - o11y_get_apm_service_latency
```

**Part 3** skills rely more on graph routing (product type) than keywords; frontmatter is mainly `name` and `description`.

### Write the Playbook Body

Use clear sections facilitators and models can scan quickly:

| Section | Purpose |
|---------|---------|
| **When to use** | Alert types, symptoms, or user intents |
| **Required context** | Service, environment, time window, IDs from Slack |
| **Tool sequence** | Ordered steps with exact MCP param names |
| **Interpretation** | How to read metrics/traces/logs |
| **Do not** | Guardrails (wrong params, skipping steps, inventing data) |
| **Final step** | Hand off to a report skill or summary format |

Copy the blank template in Part 2: `part2_agent/skills/_template/SKILL.md`.

{{< notice title="Tip" style="tip" >}}
Keep `SKILL.md` focused on workflow. Move long tables to companion files such as `reference.md` (field names, SPL hints) or `indexes.md` (Splunk index/sourcetype catalog).
{{< /notice >}}

### Add Reference Material (Optional)

Part 3's `load_skill_content(..., include_reference=True)` can append `reference.md` when needed.

{{< notice title="Important" style="primary" >}}
Never put secrets in skill files — use environment variables and `.env` for credentials.
{{< /notice >}}

### Confirm the Skill Loads and Tools Run

**Part 2**

```bash
cd part2_agent
troubleshooting-agent chat "investigate latency on Verification"
# Terminal trace should show: skill loaded=<your-skill>
```

**Part 3**

```bash
cd part3_agent
troubleshooting-agent chat "troubleshoot this APM alert"
# Galileo / terminal trace should show investigate node + skills_loaded
pytest tests/part3/test_skill_tools.py -q
```

Verify: correct tools called, parameters match the playbook, and the agent does not skip mandatory steps (e.g. log search).

### Review the Skill Design Checklist

Before merging a new skill, confirm:

- [ ] **Description** is one clear sentence — models and routers use it for selection.
- [ ] **Tool names** match what `mcp-doctor` lists (prefixes `o11y_`, `splunk_`, etc.).
- [ ] **Parameters** use nested `params` objects where MCP requires them.
- [ ] **Time ranges** are objects (`{"start": "-1h", "stop": "now"}`), not bare strings.
- [ ] **Do not** section blocks common failure modes you have seen in demos.
- [ ] **No secrets** in skills — use env/config for credentials.
- [ ] **Reference files** stay in sync when your Splunk tenant or tool schemas change.

## Review the alert-triage Skill (Part 2)

This small skill runs at the start of many investigations: confirm the alert is active and capture identifiers for later tools.

**Frontmatter** — name, description, routing signals, expected tools:

```yaml
---
name: alert-triage
description: Parse Slack O11y alerts and confirm active incidents via o11y_search_alerts_or_incidents.
alert_signals:
  - alert
  - incident
  - triggered
rule_patterns:
  - "*"
mcp_tools:
  - o11y_search_alerts_or_incidents
---
```

**Body** — when to use, context, tool sequence, response shape, guardrails:

```markdown
# Alert triage

## When to use
Any Splunk Observability alert from Slack before deeper investigation.

## Required context
- sf_service, sf_environment (exact APM names)
- time_range: {"start": "-1h", "stop": "now"}

## Tool sequence
1. o11y_search_alerts_or_incidents — params.service_name, params.environment_name, params.time_range
2. Capture eventId from results for cross-referencing in Observability Cloud

## Response template
- Alert status (active / cleared)
- Service and environment
- Recommended next playbook (latency vs errors)

## Do not
- Search without service_name
- Use time_range as a bare string
```

Full source: [`part2_agent/skills/alert-triage/SKILL.md`](https://github.com/iortiz-splunk/troubleshooting-agent/blob/main/part2_agent/skills/alert-triage/SKILL.md).

## Review the search-logs Skill (Part 3)

Part 3 treats log search as a **mandatory** cross-cutting skill — every product investigation loads it alongside the APM/IM/RUM/Synthetics playbook.

What makes this skill effective:

1. **Explicit prerequisite** — do not conclude until `splunk_run_query` runs (when Splunk MCP is connected).
2. **Catalog-first workflow** — use `indexes.md` before `splunk_get_indexes`.
3. **Copy-paste SPL patterns** — scoped to the workshop tenant (`splunk4rookies-workshop`, `kube:container:*`, `httpevent`).
4. **Companion files** — `reference.md` for field names; `indexes.md` for facilitator-maintained index discovery.

Snippet from the workflow section:

```markdown
## Catalog-first workflow (mandatory order)

1. Read the index catalog injected in your investigate prompt (`indexes.md`).
2. Collect O11y context (service, environment, pod/host/trace tags).
3. splunk_run_query with scoped SPL using the catalog index.
4. Discovery fallback only if catalog queries return zero rows.
5. Summarize findings — or state no logs found with filters tried.
```

Full source: [`part3_agent/skills/search-logs/`](https://github.com/iortiz-splunk/troubleshooting-agent/tree/main/part3_agent/skills/search-logs).

## Review the troubleshoot-apm-incidents Skill (Part 3)

Product skills are longer: they define the full O11y investigation path for one alert type. Notice how they combine **tool order**, **parameter literals**, and **cross-skill references**:

- Calls `o11y_get_apm_services`, latency/error breakdowns, exemplar traces with `exemplar_type` = `lat_buck_` (trailing underscore for latency alerts).
- Requires **search-logs** before finishing.
- Hands off to **troubleshoot-report** for the final user-facing format.

Full source: [`part3_agent/skills/troubleshoot-apm-incidents/SKILL.md`](https://github.com/iortiz-splunk/troubleshooting-agent/blob/main/part3_agent/skills/troubleshoot-apm-incidents/SKILL.md).

## Explore the Part 3 Skill Library

| Skill | Role |
|-------|------|
| `get-alerts-or-incidents` | Load and parse alert payload in **identify** |
| `troubleshoot-apm-incidents` | APM metrics, traces, infra correlation |
| `troubleshoot-im-incidents` | Infrastructure / K8s alerts |
| `troubleshoot-rum-incidents` | Real user monitoring anomalies |
| `troubleshoot-synthetics-incidents` | Synthetic check failures |
| `search-logs` | Splunk platform log search (always in **investigate**) |
| `troubleshoot-report` | Standard report sections in **report** |
| `troubleshoot` | Overview / checklist referencing other skills |

## Apply Best Practices for Effective Skills

- **Write for the model and the facilitator** — short bullets beat long prose; tables beat paragraphs.
- **Name tools exactly** as they appear in MCP — typos become failed tool calls.
- **Prefer one concern per skill** — compose with references (`Apply **search-logs** after APM tools`) instead of one giant file.
- **Version with git** — skills are code; review changes like any runbook update.
- **Refresh environment catalogs** after tenant changes — run Splunk MCP discovery and update `indexes.md` (see `part3_agent/README.md`).

## Complete the error-rate Skill Lab (Part 2)

The workshop lab asks you to complete the **`error-rate`** skill using `latency-spike` as a structural reference:

1. Edit `part2_agent/skills/error-rate/SKILL.md` — frontmatter and tool sequence.
2. Run Part 2 on an error-rate alert.
3. Confirm the trace shows `skill loaded=error-rate` and at least two MCP calls.

Details: [`part2_agent/README.md`](https://github.com/iortiz-splunk/troubleshooting-agent/blob/main/part2_agent/README.md).

---

**Next:** Continue with setup and **Part 1** when you are ready to run the baseline agent, or jump to **Part 2** to see skill injection in action.
