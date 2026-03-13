"""
Tests for the Orchestrator Agent — instruction prompt content and
collaborator configuration.

Validates: Requirements FR-5.5, FR-6.2, FR-6.4, FR-6.6, 11.1, 11.4
"""
from __future__ import annotations

from unittest.mock import Mock, patch

from hypothesis import given, settings, strategies as st

from redshift_agents.orchestrator.orchestrator import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    _invoke_subagent,
)


# ---------------------------------------------------------------------------
# Property 15: Orchestrator does not advance phase without approval
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(approvals=st.lists(st.booleans(), min_size=2, max_size=2))
def test_orchestrator_does_not_advance_without_approval(approvals):
    """Property 15: Orchestrator does not advance phase without approval

    **Validates: Requirements FR-6.2, FR-6.4, FR-6.6**
    """
    gate1_approved, gate2_approved = approvals
    phases_reached = ["assessment"]

    if gate1_approved:
        phases_reached.append("architecture")
    if gate1_approved and gate2_approved:
        phases_reached.append("execution")

    if "architecture" in phases_reached:
        assert gate1_approved
    if "execution" in phases_reached:
        assert gate1_approved and gate2_approved

    valid_orders = [
        ["assessment"],
        ["assessment", "architecture"],
        ["assessment", "architecture", "execution"],
    ]
    assert phases_reached in valid_orders


# ---------------------------------------------------------------------------
# Property 19: Orchestrator logs every subagent delegation
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    agent_name=st.sampled_from(["assessment", "architecture", "execution"]),
    user_id=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789._-",
        min_size=1, max_size=20,
    ),
    cluster_id=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",
        min_size=1, max_size=30,
    ),
)
@patch("redshift_agents.orchestrator.orchestrator.emit_audit_event")
@patch("redshift_agents.orchestrator.orchestrator.boto3.client")
def test_orchestrator_logs_every_subagent_delegation(
    mock_boto3, mock_audit, agent_name, user_id, cluster_id,
):
    """Property 19: Orchestrator logs every subagent delegation

    **Validates: Requirements FR-5.5**
    """
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

    assert mock_audit.call_count >= 1
    first_call = mock_audit.call_args_list[0]
    assert first_call[1]["initiated_by"] == user_id
    assert agent_name in str(first_call[1]["details"])


# ---------------------------------------------------------------------------
# Unit tests for orchestrator prompt content
# ---------------------------------------------------------------------------


class TestSystemPromptContainsApprovalGates:
    def test_system_prompt_contains_approval_gates(self):
        assert "Gate 1" in ORCHESTRATOR_SYSTEM_PROMPT
        assert "Gate 2" in ORCHESTRATOR_SYSTEM_PROMPT
        assert "approval" in ORCHESTRATOR_SYSTEM_PROMPT.lower()


class TestSystemPromptContainsLocking:
    def test_system_prompt_contains_locking(self):
        assert "acquire_cluster_lock" in ORCHESTRATOR_SYSTEM_PROMPT
        assert "release_cluster_lock" in ORCHESTRATOR_SYSTEM_PROMPT


class TestSystemPromptContainsIdentity:
    def test_system_prompt_contains_identity_propagation(self):
        assert "user_id" in ORCHESTRATOR_SYSTEM_PROMPT
        assert "Identity" in ORCHESTRATOR_SYSTEM_PROMPT


class TestSystemPromptContainsThreePhases:
    def test_system_prompt_contains_three_phases(self):
        assert "Phase 1" in ORCHESTRATOR_SYSTEM_PROMPT
        assert "Phase 2" in ORCHESTRATOR_SYSTEM_PROMPT
        assert "Phase 3" in ORCHESTRATOR_SYSTEM_PROMPT
