"""
Unit tests for Assessment Agent tool wiring and system prompt.

Validates: FR-2.7
"""
from redshift_agents.subagents.assessment import create_agent, ASSESSMENT_SYSTEM_PROMPT


class TestCreateAgentDefaultTools:
    """Verify create_agent() wires the 4 expected assessment tools by default."""

    def test_create_agent_default_tools(self):
        agent = create_agent()
        assert len(agent.tools) == 4
        tool_names = [t.__name__ for t in agent.tools]
        assert "list_redshift_clusters" in tool_names
        assert "analyze_redshift_cluster" in tool_names
        assert "get_cluster_metrics" in tool_names
        assert "get_wlm_configuration" in tool_names


class TestCreateAgentCustomTools:
    """Verify create_agent(tools=[...]) uses the caller-supplied tools."""

    def test_create_agent_custom_tools(self):
        def my_custom_tool():
            pass

        agent = create_agent(tools=[my_custom_tool])
        assert len(agent.tools) == 1
        assert agent.tools[0] is my_custom_tool


class TestSystemPromptContainsKeyInstructions:
    """Verify ASSESSMENT_SYSTEM_PROMPT contains key domain phrases."""

    def test_system_prompt_contains_key_instructions(self):
        assert "WLM" in ASSESSMENT_SYSTEM_PROMPT
        assert "contention" in ASSESSMENT_SYSTEM_PROMPT
        assert "cluster_summary" in ASSESSMENT_SYSTEM_PROMPT
        assert "wlm_queue_analysis" in ASSESSMENT_SYSTEM_PROMPT
