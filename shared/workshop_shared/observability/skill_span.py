"""Emit skill-load actions as LangChain child spans (visible in Galileo under each agent node)."""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig, RunnableLambda


async def emit_skill_load(
    parent_config: RunnableConfig,
    *,
    skill_name: str,
    role: str,
    chars: int | None = None,
    detail: str | None = None,
    span_kind: str = "load",
) -> dict[str, Any]:
    """Emit a skill span under the current graph node.

    span_kind:
      - ``load`` (default): skill content injected into an LLM prompt → ``load_skill:<name>``
      - ``route``: code-only routing decision, no prompt injection → ``route_skill:<name>``
    """
    is_route = span_kind == "route"
    span_prefix = "route_skill" if is_route else "load_skill"
    action_verb = "Routed to skill" if is_route else "Loaded skill"

    async def _marker(_: Any) -> dict[str, Any]:
        output: dict[str, Any] = {
            "skill": skill_name,
            "role": role,
            "action": f"{action_verb} `{skill_name}`",
        }
        if chars is not None:
            output["chars_injected"] = chars
        if detail:
            output["detail"] = detail
        return output

    base = dict(parent_config)
    metadata = dict(base.get("metadata") or {})
    metadata["agent.skill_loaded"] = skill_name
    metadata["agent.skill_role"] = role
    metadata["agent.skill_span_kind"] = span_kind
    if chars is not None:
        metadata["agent.skill_chars_injected"] = str(chars)
    if detail:
        metadata["agent.skill_detail"] = detail

    tags = list(base.get("tags") or [])
    tag = f"{span_prefix}:{skill_name}"
    if tag not in tags:
        tags.append(tag)

    load_config = RunnableConfig(
        **{
            **base,
            "run_name": f"{span_prefix}:{skill_name}",
            "metadata": metadata,
            "tags": tags,
        }
    )

    span_input = f"{action_verb} `{skill_name}` ({role})"
    if detail:
        span_input += f"; {detail}"

    return await RunnableLambda(_marker).ainvoke({"input": span_input}, config=load_config)
