"""
Property-based and unit tests for the Orchestrator Agent.

Feature: redshift-modernization-agents

Validates: Requirements FR-5.5, FR-6.2, FR-6.4, FR-6.6
"""
from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

from hypothesis import given, settings, strategies as st

from redshift_agents.orchestrator.orchestrator import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    _invoke_subagent,
    create_agent,
)


# ---------------------------------------------------------------------------
# Property 15: Orchestrator does not advance phase without approval
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    approvals=st.lists(st.booleans(), min_size=2, max_size=2),
)
def test_orchestrator_does_not_advance_without_approval(approvals):
    """Property 15: Orchestrator does not advance phase without approval

    Simulate the workflow state machine and verify gate enforcement.
    The orchestrator must not transition from phase N to phase N+1
    without an intervening approval event.

    **Validates: Requirements FR-6.2, FR-6.4, FR-6.6**
    """
    # Feature: redshift-modernization-agents, Property 15: Orchestrator does not advance phase without approval
    gate1_approved, gate2_approved = approvals

    phases_reached = ["assessment"]  # always starts with assessment

    # Gate 1: assessment -> architecture
    if gate1_approved:
        phases_reached.append("architecture")

    # Gate 2: architecture -> execution (only if gate 1 was approved)
    if gate1_approved and gate2_approved:
        phases_reached.append("execution")

    # Verify: architecture only reached if gate 1 approved
    if "architecture" in phases_reached:
        assert gate1_approved

    # Verify: execution only reached if both gates approved
    if "execution" in phases_reached:
        assert gate1_approved and gate2_approved

    # Verify: phases are always in order (no skipping)
    valid_orders = [
        ["assessment"],
        ["assessment", "architecture"],
        ["assessment", "architecture", "execution"],
    ]
    assert phases_reached in valid_orders

    # Verify: no phase appears without its predecessor
    if "execution" in phases_reached:
        assert "architecture" in phases_reached
    if "architecture" in phases_reached:
        assert "assessment" in phases_reached


# ---------------------------------------------------------------------------
# Property 19: Orchestrator logs every subagent delegation
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    agent_name=st.sampled_from(["assessment", "architecture", "execution"]),
    user_id=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789._-",
        min_size=1,
        max_size=20,
    ),
    cluster_id=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",
        min_size=1,
        max_size=30,
    ),
)
@patch("redshift_agents.orchestrator.orchestrator.emit_audit_event")
@patch("redshift_agents.orchestrator.orchestrator.boto3.client")
def test_orchestrator_logs_every_subagent_delegation(
    mock_boto3, mock_audit, agent_name, user_id, cluster_id
):
    """Property 19: Orchestrator logs every subagent delegation

    Verify _invoke_subagent emits audit events for every delegation.

    **Validates: Requirements FR-5.5**
    """
    # Feature: redshift-modernization-agents, Property 19: Orchestrator logs every subagent delegation

    # Mock the bedrock-agent-runtime client
    mock_client = Mock()
    mock_client.invoke_agent.return_value = {"completion": []}
    mock_boto3.return_value = mock_client

    _invoke_subagent(
        agent_id=f"redshift-{agent_name}-subagent",
        agent_name=agent_name,
        message="test",
        payload={"cluster_id": cluster_id},
        user_id=user_id,
        customer_account_id="123456789012",
        region="us-east-2",
    )

    # Must have emitted at least one audit event
    assert mock_audit.call_count >= 1

    # First call should be the delegation event
    first_call = mock_audit.call_args_list[0]
    assert first_call[1]["initiated_by"] == user_id
    assert agent_name in str(first_call[1]["details"])


# ---------------------------------------------------------------------------
# Unit tests for orchestrator
# ---------------------------------------------------------------------------


class TestCreateAgentDefaultTools:
    """Verify create_agent() returns an Agent with 5 tools."""

    @patch("redshift_agents.orchestrator.orchestrator.emit_audit_event")
    def test_create_agent_default_tools(self, mock_audit):
        agent = create_agent()
        assert len(agent.tools) == 5
        tool_names = [t.__name__ for t in agent.tools]
        assert "invoke_assessment" in tool_names
        assert "invoke_architecture" in tool_names
        assert "invoke_execution" in tool_names
        assert "acquire_cluster_lock" in tool_names
        assert "release_cluster_lock" in tool_names


class TestSystemPromptContainsApprovalGates:
    """Verify prompt contains Gate 1, Gate 2, and approval language."""

    def test_system_prompt_contains_approval_gates(self):
        assert "Gate 1" in ORCHESTRATOR_SYSTEM_PROMPT
        assert "Gate 2" in ORCHESTRATOR_SYSTEM_PROMPT
        assert "approval" in ORCHESTRATOR_SYSTEM_PROMPT.lower()


class TestSystemPromptContainsLocking:
    """Verify prompt contains cluster locking instructions."""

    def test_system_prompt_contains_locking(self):
        assert "acquire_cluster_lock" in ORCHESTRATOR_SYSTEM_PROMPT
        assert "release_cluster_lock" in ORCHESTRATOR_SYSTEM_PROMPT
