"""
Redshift Modernization Orchestrator using Strands Agent.

Coordinates the complete Redshift modernization workflow by delegating
tasks to specialized subagents via Bedrock AgentCore InvokeAgent API.
Enforces approval gates between phases, acquires cluster-level locks,
propagates user identity, and logs every subagent delegation.

Requirements: FR-1.1, FR-1.2, FR-1.3, FR-1.4, FR-5.5, FR-6.1–FR-6.6,
              NFR-1.1, NFR-2.2, NFR-2.3
"""
from __future__ import annotations

import json
import os
from typing import Dict

import boto3
from strands import Agent
from strands.tools import tool

from ..tools.audit_logger import emit_audit_event
from ..tools.cluster_lock import acquire_lock, release_lock

# ---------------------------------------------------------------------------
# Orchestrator tools — each delegates to a subagent via InvokeAgent API
# ---------------------------------------------------------------------------

ASSESSMENT_AGENT_ID = os.getenv(
    "ASSESSMENT_AGENT_ID", "redshift-assessment-subagent"
)
ARCHITECTURE_AGENT_ID = os.getenv(
    "ARCHITECTURE_AGENT_ID", "redshift-architecture-subagent"
)
EXECUTION_AGENT_ID = os.getenv(
    "EXECUTION_AGENT_ID", "redshift-execution-subagent"
)


def _invoke_subagent(
    agent_id: str,
    agent_name: str,
    message: str,
    payload: Dict,
    user_id: str,
    customer_account_id: str,
    region: str,
) -> Dict:
    """Invoke a subagent via Bedrock AgentCore InvokeAgent API.

    Emits an audit event for delegation logging (FR-5.5) and propagates
    identity (NFR-7.1).

    Args:
        agent_id: The AgentCore agent identifier.
        agent_name: Human-readable name for audit logging.
        message: The instruction message for the subagent.
        payload: Additional payload fields (cluster_id, assessment_results, etc.).
        user_id: Identity of the person who triggered the workflow.
        customer_account_id: AWS account ID of the customer.
        region: AWS region for the AgentCore runtime client.

    Returns:
        Dict with the subagent response or an error dict.
    """
    # Build the input payload with identity propagation
    input_payload = {
        "message": message,
        "user_id": user_id,
        "customer_account_id": customer_account_id,
        "region": region,
        **payload,
    }

    # Emit delegation audit event (task 11.4 — FR-5.5)
    emit_audit_event(
        event_type="tool_invocation",
        agent_name="orchestrator",
        customer_account_id=customer_account_id,
        initiated_by=user_id,
        cluster_id=payload.get("cluster_id", ""),
        region=region,
        details={
            "action": "invoke_subagent",
            "subagent_name": agent_name,
            "subagent_id": agent_id,
            "input_payload": input_payload,
        },
    )

    try:
        client = boto3.client("bedrock-agent-runtime", region_name=region)
        response = client.invoke_agent(
            agentId=agent_id,
            inputText=json.dumps(input_payload),
        )

        # Extract completion from the response stream
        result_text = ""
        if "completion" in response:
            for event in response["completion"]:
                if "chunk" in event:
                    result_text += event["chunk"].get("bytes", b"").decode(
                        "utf-8", errors="replace"
                    )

        result_summary = result_text[:500] if result_text else "No response"

        # Emit audit event with result summary (task 11.4)
        emit_audit_event(
            event_type="tool_invocation",
            agent_name="orchestrator",
            customer_account_id=customer_account_id,
            initiated_by=user_id,
            cluster_id=payload.get("cluster_id", ""),
            region=region,
            details={
                "action": "subagent_response",
                "subagent_name": agent_name,
                "result_summary": result_summary,
            },
        )

        return {
            "subagent": agent_name,
            "response": result_text,
            "status": "success",
        }
    except Exception as exc:
        error_msg = str(exc)
        emit_audit_event(
            event_type="error",
            agent_name="orchestrator",
            customer_account_id=customer_account_id,
            initiated_by=user_id,
            cluster_id=payload.get("cluster_id", ""),
            region=region,
            details={
                "action": "invoke_subagent",
                "subagent_name": agent_name,
                "error": error_msg,
            },
        )
        return {
            "subagent": agent_name,
            "error": error_msg,
            "status": "failed",
        }


@tool
def invoke_assessment(
    cluster_id: str,
    region: str,
    customer_account_id: str,
    user_id: str,
) -> Dict:
    """Invoke the assessment subagent via Bedrock AgentCore InvokeAgent API.

    Delegates cluster analysis to the assessment subagent, which performs
    WLM queue analysis, CloudWatch metrics retrieval, and contention detection.

    Args:
        cluster_id: Redshift cluster identifier to assess.
        region: AWS region where the cluster resides.
        customer_account_id: Customer AWS account ID.
        user_id: Identity of the person who triggered the workflow.

    Returns:
        Dict with assessment results or error information.
    """
    return _invoke_subagent(
        agent_id=ASSESSMENT_AGENT_ID,
        agent_name="assessment",
        message=f"Analyze Redshift cluster {cluster_id} in {region}. "
        f"Perform WLM queue analysis, retrieve CloudWatch metrics, "
        f"and identify contention problems.",
        payload={"cluster_id": cluster_id},
        user_id=user_id,
        customer_account_id=customer_account_id,
        region=region,
    )


@tool
def invoke_architecture(
    assessment_results: str,
    region: str,
    customer_account_id: str,
    user_id: str,
) -> Dict:
    """Invoke the architecture subagent via Bedrock AgentCore InvokeAgent API.

    Delegates workgroup design to the architecture subagent, which proposes
    WLM-to-workgroup mapping, RPU sizing, and architecture pattern selection.

    Args:
        assessment_results: JSON string of assessment output from Phase 1.
        region: AWS region for the target architecture.
        customer_account_id: Customer AWS account ID.
        user_id: Identity of the person who triggered the workflow.

    Returns:
        Dict with architecture design or error information.
    """
    return _invoke_subagent(
        agent_id=ARCHITECTURE_AGENT_ID,
        agent_name="architecture",
        message=f"Design Serverless workgroup architecture based on assessment results. "
        f"Propose workgroup split, RPU sizing (minimum 32), and architecture pattern.",
        payload={"assessment_results": assessment_results},
        user_id=user_id,
        customer_account_id=customer_account_id,
        region=region,
    )


@tool
def invoke_execution(
    architecture_results: str,
    region: str,
    customer_account_id: str,
    user_id: str,
) -> Dict:
    """Invoke the execution subagent via Bedrock AgentCore InvokeAgent API.

    Delegates migration execution to the execution subagent, which creates
    namespace/workgroups, restores snapshots, sets up data sharing, and
    validates performance.

    Args:
        architecture_results: JSON string of architecture design from Phase 2.
        region: AWS region for the target Serverless resources.
        customer_account_id: Customer AWS account ID.
        user_id: Identity of the person who triggered the workflow.

    Returns:
        Dict with execution results or error information.
    """
    return _invoke_subagent(
        agent_id=EXECUTION_AGENT_ID,
        agent_name="execution",
        message=f"Execute migration plan based on architecture design. "
        f"Create namespace/workgroups, restore snapshot, set up data sharing, "
        f"migrate users, and validate performance.",
        payload={"architecture_results": architecture_results},
        user_id=user_id,
        customer_account_id=customer_account_id,
        region=region,
    )


@tool
def acquire_cluster_lock(
    cluster_id: str,
    user_id: str,
    region: str = "us-east-2",
) -> Dict:
    """Acquire a cluster-level lock before starting workflow.

    Prevents two users from working on the same cluster simultaneously.
    Uses DynamoDB conditional writes for atomicity with a 24-hour TTL
    safety net.

    Args:
        cluster_id: Redshift cluster identifier to lock.
        user_id: Identity of the user requesting the lock.
        region: AWS region for the DynamoDB lock table.

    Returns:
        Dict with lock acquisition result including holder info on denial.
    """
    return acquire_lock(cluster_id, user_id, region)


@tool
def release_cluster_lock(
    cluster_id: str,
    user_id: str,
    region: str = "us-east-2",
) -> Dict:
    """Release a cluster-level lock on workflow completion or failure.

    Only the current lock holder can release. On failure, the 24-hour TTL
    acts as a safety net.

    Args:
        cluster_id: Redshift cluster identifier to unlock.
        user_id: Identity of the user releasing the lock.
        region: AWS region for the DynamoDB lock table.

    Returns:
        Dict with release result.
    """
    return release_lock(cluster_id, user_id, region)


# ---------------------------------------------------------------------------
# System prompt — covers all orchestrator responsibilities
# ---------------------------------------------------------------------------

ORCHESTRATOR_SYSTEM_PROMPT = """You are the Redshift Modernization Orchestrator for AWS.

Your mission is to guide customers through comprehensive Redshift Provisioned-to-Serverless
modernization. You coordinate a three-phase workflow, enforce approval gates, manage cluster
locks, propagate user identity, and log every subagent delegation.

You and all subagents run within the customer's AWS account — there is no separate service account.

## CRITICAL: Identity Requirement

Every request MUST include a `user_id`. If a request is missing `user_id`, you MUST reject it
immediately with a clear error message:
"Error: user_id is required for all modernization workflows. Please provide your user_id."

Do NOT proceed with any workflow step without a valid `user_id`.

## Workflow: Three Phases with Approval Gates

### Phase 1: Discovery & Assessment
1. Collect cluster identifier, region, and customer_account_id from the user.
2. Acquire a cluster lock using `acquire_cluster_lock(cluster_id, user_id, region)`.
   - If the lock is denied, inform the user who holds the lock and when it was acquired.
   - Do NOT proceed if the lock cannot be acquired.
3. Invoke `invoke_assessment(cluster_id, region, customer_account_id, user_id)`.
4. Present the assessment results (WLM queue analysis, contention findings) to the user.

### Gate 1: Assessment → Architecture Approval
- After presenting assessment results, you MUST ask the user for explicit approval.
- Say: "Based on the assessment, I recommend proceeding to architecture design. Do you approve?"
- Wait for the user's response.
- If APPROVED: proceed to Phase 2.
- If REJECTED: inform the user and offer to restart the assessment or modify parameters.
- You MUST NOT invoke `invoke_architecture` without explicit user approval.

### Phase 2: Architecture Design
1. Invoke `invoke_architecture(assessment_results, region, customer_account_id, user_id)`.
2. Present the proposed architecture (workgroup split, RPU sizing, cost estimates) to the user.

### Gate 2: Architecture → Execution Approval
- After presenting the architecture proposal, you MUST ask the user for explicit approval.
- Say: "Here is the proposed architecture. Do you approve proceeding to execution?"
- Wait for the user's response.
- If APPROVED: proceed to Phase 3.
- If REJECTED: inform the user and offer to redesign or adjust parameters.
- You MUST NOT invoke `invoke_execution` without explicit user approval.

### Phase 3: Migration Execution
1. Invoke `invoke_execution(architecture_results, region, customer_account_id, user_id)`.
2. Present the execution results (migration status, validation results) to the user.
3. Release the cluster lock using `release_cluster_lock(cluster_id, user_id, region)`.

## Cluster Locking (NFR-2.2, NFR-2.3)

- ALWAYS acquire a cluster lock at the start of the workflow (before Phase 1 assessment).
- ALWAYS release the cluster lock when the workflow completes (after Phase 3) or if any phase fails.
- If lock acquisition fails, inform the user:
  "Cluster {cluster_id} is currently locked by {lock_holder} since {acquired_at}.
   Please wait for the other workflow to complete or contact {lock_holder}."
- On any error or workflow termination, release the lock before stopping.

## Approval Gate Rules (FR-6.2, FR-6.4, FR-6.6)

- You MUST NOT advance from Phase 1 to Phase 2 without Gate 1 approval.
- You MUST NOT advance from Phase 2 to Phase 3 without Gate 2 approval.
- On rejection at any gate:
  1. Acknowledge the rejection.
  2. Offer options: restart the current phase, modify parameters, or end the workflow.
  3. If ending the workflow, release the cluster lock.

## Subagent Delegation Logging (FR-5.5)

- Every subagent invocation is automatically logged by the invoke_* tools.
- Each log entry includes: which subagent, the input payload, and the result summary.
- You do not need to manually log delegations — the tools handle this.

## Identity Propagation (NFR-7.1)

- Every tool call and subagent invocation MUST include the `user_id`.
- The `user_id` flows: orchestrator → subagent payload → tool calls → audit logs → Redshift Data API.
- Never omit `user_id` from any invocation.

## Error Handling

- If a subagent invocation fails, present the error to the user and offer to retry.
- If a phase fails after partial execution, inform the user about rollback options.
- On any unrecoverable error, release the cluster lock and inform the user.
- Never silently swallow errors — always surface them to the user.

## Communication Style

- Be clear and professional.
- Explain technical concepts in accessible terms.
- Provide actionable recommendations.
- Summarize subagent results in customer-friendly language.
- Keep customers informed of progress at each step.
"""


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


def create_agent(tools=None):
    """Create the Orchestrator Agent with Strands framework.

    Args:
        tools: Optional list of tool functions. Defaults to the standard
            orchestrator tool set (invoke_assessment, invoke_architecture,
            invoke_execution, acquire_cluster_lock, release_cluster_lock).

    Returns:
        A configured Strands Agent instance for workflow orchestration.
    """
    emit_audit_event(
        event_type="agent_start",
        agent_name="orchestrator",
        details={"action": "create_agent"},
    )
    return Agent(
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        tools=tools
        or [
            invoke_assessment,
            invoke_architecture,
            invoke_execution,
            acquire_cluster_lock,
            release_cluster_lock,
        ],
    )


# ---------------------------------------------------------------------------
# BedrockAgentCoreApp entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from bedrock_agentcore.runtime import BedrockAgentCoreApp

    app = BedrockAgentCoreApp(agent_factory=create_agent)
    app.serve()
