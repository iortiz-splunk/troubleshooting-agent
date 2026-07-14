"""Tests for final response extraction."""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from part1_agent.agent import _extract_final_response


def test_extract_final_response_does_not_append_json_on_follow_up_question() -> None:
    """Regression: 'Would you like me to proceed?' must not dump raw MCP JSON."""
    huge_json = '{"summary":{"requestCount":{"valueByTime":[' + "1," * 5000 + "1]}}}"
    messages = [
        HumanMessage(content="investigate"),
        AIMessage(content="", tool_calls=[{"name": "o11y_get_apm_service_latency", "args": {}, "id": "1"}]),
        ToolMessage(content=huge_json, tool_call_id="1"),
        AIMessage(
            content=(
                "Findings:\n- p99 latency elevated.\n\n"
                "Next step, I can fetch exemplar traces. Would you like me to proceed?"
            )
        ),
    ]
    result = _extract_final_response(messages)
    assert "Would you like me to proceed" in result
    assert "--- Observability data ---" not in result
    assert "valueByTime" not in result


def test_extract_final_response_appends_short_excerpt_on_thin_failure() -> None:
    huge_json = '{"error":"missing environment_name"}' + "x" * 5000
    messages = [
        HumanMessage(content="investigate"),
        ToolMessage(content=huge_json, tool_call_id="1"),
        AIMessage(content="There is an issue with the required parameter. Please provide environment_name."),
    ]
    result = _extract_final_response(messages)
    assert "--- Observability data ---" in result
    assert len(result) < len(huge_json)
