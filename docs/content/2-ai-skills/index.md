---
title: "AI Skills"
description: "What AI skills (playbooks) are, why they matter for reliable agents, and how they differ from tools and prompts."
weight: 2
navTitle: "AI Skills"
---

An **AI skill** (also called a **playbook**) is a markdown file that tells the agent *how* to investigate — which tools to call, in what order, with which parameters, and what guardrails to follow. Skills do not replace tools; they **guide** the model so investigations are repeatable, grounded, and safe.

Think of it this way: **tools** are what the agent *can* do (query a database, search logs, fetch metrics). A **skill** is the procedure you want it to *follow* when doing a specific kind of work — like an SOP, runbook, or checklist you would give a new team member. The language model reads the skill and uses it to decide how to apply its tools.

In this workshop, skills live under `skills/<skill-name>/SKILL.md`. You will author and run them hands-on in [Part 2]({{< ref "8-part2-skill-playbooks" >}}) and see them load at each workflow step in [Part 3]({{< ref "9-part3-full-workflow" >}}).

## Why skills matter

An AI agent without skills still has access to tools and a general system prompt — but every run is an open-ended problem. The model must figure out the steps on its own: what to check first, which API parameters to use, when to stop, and how to format the answer. That works for simple questions, but operational tasks (incident response, compliance checks, customer support escalations) need **consistent, auditable steps**.

Skills encode **operational knowledge** that models do not reliably invent on their own:

| Without skills | With skills |
|----------------|-------------|
| Skips important steps (e.g. checks metrics but never searches logs) | Explicit **workflow order** — step 1, step 2, step 3 |
| Uses wrong parameters or formats | **Parameter hints** and **do-not** rules |
| Looks up data in the wrong place (wrong index, wrong environment) | **Environment catalogs** and scoped references |
| States conclusions when tools returned nothing | **Guardrails** — say "no data found," do not guess |
| Different answer every time on the same input | **Repeatable playbooks** teams can review and improve |

Skills are especially valuable in production because they:

- **Reduce hallucination risk** — steer the agent toward tool output, not free-form guessing
- **Capture tribal knowledge** — senior operators' runbooks become version-controlled files, not one-off chat prompts
- **Improve observability** — traces can show *which playbook* ran, making debugging and evaluation easier
- **Enable safe iteration** — tighten one skill without rewriting the whole agent

{{< notice title="Workshop tie-in" style="tip" >}}
In [Part 1]({{< ref "6-part1-baseline-agent" >}}) you run an agent with **tools only** — no skills. Parts 2 and 3 add playbooks so you can compare how much structure improves investigation quality on the same alert.
{{< /notice >}}

## Skills, tools, and prompts — three different layers

When you design an agent, keep these roles separate:

| Layer | What it is | General example | Workshop example |
|-------|------------|-----------------|------------------|
| **System prompt** | Standing instructions for every run — tone, safety, global rules | "You are a helpful support agent. Never share internal credentials." | Base instructions in `prompt.py` |
| **Tools** | Callable functions that fetch data or take action in external systems | `search_tickets`, `get_account_balance`, `run_database_query` | `o11y_get_apm_service_latency`, `splunk_run_query` |
| **Skills** | Task-specific procedures injected when a particular kind of work starts | "Refund escalation playbook" or "latency investigation runbook" | `latency-spike`, `troubleshoot-apm-incidents` |

The model **chooses** among the tools you expose (within framework limits). Skills **constrain and sequence** that choice so the work matches your standards — they do not execute tools themselves; they tell the model what to aim for.

{{< notice title="Important" style="primary" >}}
Skills are **not** tools. A skill is text guidance loaded into the agent's context. Tools are the actual API calls. Confusing the two is a common mistake when reading agent traces.
{{< /notice >}}

## What goes inside a skill

Most skills are plain markdown files — easy for humans to read and edit, easy for models to follow. A typical structure:

| Section | Purpose |
|---------|---------|
| **When to use** | Symptoms, alert types, or user intents that match this playbook |
| **Required context** | What the agent must know before acting (IDs, time window, environment) |
| **Steps / tool sequence** | Ordered actions — often mapped to specific tools |
| **Interpretation** | How to read results — not just what to call |
| **Do not** | Guardrails: skip steps, wrong formats, inventing data |
| **Output format** | How to hand off or report (sometimes a separate reporting skill) |

Many implementations add a short **metadata block** at the top (name, description, keywords for routing). Optional **companion files** hold long reference tables — field names, index catalogs, query templates — so the main skill stays scannable.

{{< notice title="Tip" style="tip" >}}
Write skills for **both** the model and your team: short bullets, clear headings, and concrete examples beat long prose.
{{< /notice >}}

## How agents load and use skills

Frameworks differ in *when* a skill enters the conversation, but the idea is the same: the playbook text is appended to the agent's instructions for that run (or that workflow step).

| Pattern | How it works | When it fits |
|---------|--------------|--------------|
| **Upfront injection** | Match the user's message or alert to a skill, load it before the first model turn | Simple agents, keyword routing, fast prototypes |
| **Per workflow step** | Different skills at different stages (identify → investigate → report) | Production workflows with explicit phases |
| **On demand** | Agent or router calls a "load skill" tool when it recognizes the task | Large skill libraries, dynamic runbooks |

You do not need to implement routing yourself on day one — the workshop shows two common patterns:

- **Part 2** — one domain skill plus a reporting skill, injected **upfront** via keyword matching
- **Part 3** — different skills at each **graph node** (alert identification, product-specific investigation, final report)

Same `SKILL.md` file format; different orchestration around it.

## Example: a small triage skill

Below is a simplified alert-triage playbook from this repo. Notice how it states *when* to use the skill, *what* context is required, *which* tools to call in order, and *what not* to do — without any Python code.

```yaml
---
name: alert-triage
description: Confirm an observability alert is active and capture identifiers for follow-up steps.
---
```

```markdown
# Alert triage

## When to use
Before deeper investigation on any monitoring alert.

## Required context
- Service and environment names (exact values from the alert)
- Time window for the investigation (e.g. last hour)

## Steps
1. Search for matching alerts or incidents — filter by service and environment
2. Record alert ID and status (active / cleared) for later steps

## Do not
- Skip the search when the user pasted partial alert text
- Invent alert IDs if the search returns nothing — say what you tried
```

Full source: [`part2_agent/skills/alert-triage/SKILL.md`](https://github.com/iortiz-splunk/troubleshooting-agent/blob/main/part2_agent/skills/alert-triage/SKILL.md).

Larger skills in this workshop add product-specific steps (APM latency, log search, structured reports). The pattern is the same: **procedure in markdown**, loaded when the agent needs that kind of expertise.

## Best practices

- **One concern per skill** — compose smaller playbooks ("search logs," "format report") instead of one giant file
- **Name tools exactly** as your agent exposes them — typos become failed calls
- **Be explicit about empty results** — "no data found" is a valid outcome; guessing is not
- **Version skills like code** — review changes in git; runbooks drift if nobody owns them
- **Never put secrets in skill files** — credentials belong in environment variables or a secrets manager
- **Keep environment-specific catalogs separate** — index names, field maps, and tenant tables change; companion files are easier to refresh

## What you will do in the workshop

This page is conceptual background. Hands-on work comes later:

| When | What |
|------|------|
| [Part 1]({{< ref "6-part1-baseline-agent" >}}) | Agent with tools only — baseline with no playbooks |
| [Part 2]({{< ref "8-part2-skill-playbooks" >}}) | Run a skill-injected agent; complete the **`error-rate`** skill lab |
| [Part 3]({{< ref "9-part3-full-workflow" >}}) | Full workflow — skills load per graph node, including log search and structured reports |

Skill authoring details (YAML fields, checklist, MCP tool names) are covered in Part 2 when you edit `SKILL.md` files yourself.

---

**Next:** [Connect to EC2]({{< ref "3-connect-ec2" >}}) when you are ready to set up your workshop environment, or return to [Overview of AI Agents]({{< ref "1-ai-agents-overview" >}}) if you want to review orchestration and tools first.
