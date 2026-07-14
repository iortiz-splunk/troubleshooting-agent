"""Tests for Part 3 graph observability helpers."""

from part3_agent.graph import Part3State, _node_config


def test_node_config_sets_agent_node_metadata() -> None:
    state: Part3State = {
        "product_type": "apm",
        "skills_loaded": ["get-alerts-or-incidents", "troubleshoot-apm-incidents"],
    }
    config = _node_config(None, "investigate", state)
    metadata = config.get("metadata") or {}
    assert metadata.get("agent.node") == "investigate"
    assert metadata.get("agent.product_type") == "apm"
    assert "troubleshoot-apm-incidents" in metadata.get("agent.skills_loaded", "")
    assert config.get("run_name") == "investigate"
