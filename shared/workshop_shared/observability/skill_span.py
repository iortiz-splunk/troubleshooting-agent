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
) -> dict[str, Any]:
    """Run a short child chain named load_skill:<skill> under the current graph node."""

    async def _marker(_: Any) -> dict[str, Any]:
        output: dict[str, Any] = {
            "skill": skill_name,
            "role": role,
            "action": f"Loaded skill `{skill_name}` into agent context",
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
    if chars is not None:
        metadata["agent.skill_chars_injected"] = str(chars)
    if detail:
        metadata["agent.skill_detail"] = detail

    tags = list(base.get("tags") or [])
    tag = f"load_skill:{skill_name}"
    if tag not in tags:
        tags.append(tag)

    load_config = RunnableConfig(
        **{
            **base,
            "run_name": f"load_skill:{skill_name}",
            "metadata": metadata,
            "tags": tags,
        }
    )

    span_input = f"Load skill `{skill_name}` ({role})"
    if detail:
        span_input += f"; {detail}"

    return await RunnableLambda(_marker).ainvoke({"input": span_input}, config=load_config)
