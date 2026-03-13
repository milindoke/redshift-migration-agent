"""
Redshift Modernization Orchestrator.

Contains the system prompt constant used by the CDK stack to configure
the Orchestrator (Supervisor) Bedrock Agent. Also retains the
``_invoke_subagent`` helper for programmatic subagent delegation via
the Bedrock Agent Runtime InvokeAgent API.

Requirements: FR-1.1, FR-1.2, FR-1.3, FR-1.4, FR-5.5, FR-6.1-FR-6.6,
              NFR-1.1, NFR-2.2, NFR-2.3
"""
from __future__ import annotations

import json
import os
from typing import Dict

import boto3

from ..tools.audit_logger import emit_audit_event
from ..tools.cluster_lock import acquire_lock, release_lock

# ---------------------------------------------------------------------------
# Subagent IDs (set after CDK deployment)
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
    """Invoke a subagent via Bedrock Agent Runtime InvokeAgent API.

    Emits an audit event for delegation logging (FR-5.5) and propagates
    identity (NFR-7.1).
    """
    input_payload = {
        "message": message,
        "user_id": user_id,
        "customer_account_id": customer_account_id,
        "region": region,
        **payload,
    }

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

        result_text = ""
        if "completion" in response:
            for event in response["completion"]:
                if "chunk" in event:
                    result_text += event["chunk"].get("bytes", b"").decode(
                        "utf-8", errors="replace"
                    )

        result_summary = result_text[:500] if result_text else "No response"

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


def invoke_assessment(
    cluster_id: str, region: str, customer_account_id: str, user_id: str,
) -> Dict:
    """Invoke the assessment subagent."""
    return _invoke_subagent(
        agent_id=ASSESSMENT_AGENT_ID, agent_name="assessment",
        message=f"Analyze Redshift cluster {cluster_id} in {region}. "
        f"Perform WLM queue analysis, retrieve CloudWatch metrics, "
        f"and identify contention problems.",
        payload={"cluster_id": cluster_id},
        user_id=user_id, customer_account_id=customer_account_id, region=region,
    )


def invoke_architecture(
    assessment_results: str, region: str, customer_account_id: str, user_id: str,
) -> Dict:
    """Invoke the architecture subagent."""
    return _invoke_subagent(
        agent_id=ARCHITECTURE_AGENT_ID, agent_name="architecture",
        message="Design Serverless workgroup architecture based on assessment results. "
        "Propose workgroup split, RPU sizing (minimum 32), and architecture pattern.",
        payload={"assessment_results": assessment_results},
        user_id=user_id, customer_account_id=customer_account_id, region=region,
    )


def invoke_execution(
    architecture_results: str, region: str, customer_account_id: str, user_id: str,
) -> Dict:
    """Invoke the execution subagent."""
    return _invoke_subagent(
        agent_id=EXECUTION_AGENT_ID, agent_name="execution",
        message="Execute migration plan based on architecture design. "
        "Create namespace/workgroups, restore snapshot, set up data sharing, "
        "migrate users, and validate performance.",
        payload={"architecture_results": architecture_results},
        user_id=user_id, customer_account_id=customer_account_id, region=region,
    )


def acquire_cluster_lock(
    cluster_id: str, user_id: str, region: str = "us-east-2",
) -> Dict:
    """Acquire a cluster-level lock before starting workflow."""
    return acquire_lock(cluster_id, user_id, region)


def release_cluster_lock(
    cluster_id: str, user_id: str, region: str = "us-east-2",
) -> Dict:
    """Release a cluster-level lock on workflow completion or failure."""
    return release_lock(cluster_id, user_id, region)


# ---------------------------------------------------------------------------
# System prompt -- covers all orchestrator responsibilities
# ---------------------------------------------------------------------------

ORCHESTRATOR_SYSTEM_PROMPT = """You are the Redshift Modernization Orchestrator for AWS.

Your mission is to guide customers through comprehensive Redshift Provisioned-to-Serverless
modernization. You coordinate a three-phase workflow, enforce approval gates, manage cluster
locks, propagate user identity, and log every subagent delegation.

You and all subagents run within the customer's AWS account -- there is no separate service account.

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

### Gate 1: Assessment to Architecture Approval
- After presenting assessment results, you MUST ask the user for explicit approval.
- Say: "Based on the assessment, I recommend proceeding to architecture design. Do you approve?"
- Wait for the user's response.
- If APPROVED: proceed to Phase 2.
- If REJECTED: inform the user and offer to restart the assessment or modify parameters.
- You MUST NOT invoke `invoke_architecture` without explicit user approval.

### Phase 2: Architecture Design
1. Invoke `invoke_architecture(assessment_results, region, customer_account_id, user_id)`.
2. Present the proposed architecture (workgroup split, RPU sizing, cost estimates) to the user.

### Gate 2: Architecture to Execution Approval
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
- You do not need to manually log delegations -- the tools handle this.

## Identity Propagation (NFR-7.1)

- Every tool call and subagent invocation MUST include the `user_id`.
- The `user_id` flows: orchestrator -> subagent payload -> tool calls -> audit logs -> Redshift Data API.
- Never omit `user_id` from any invocation.

## Error Handling

- If a subagent invocation fails, present the error to the user and offer to retry.
- If a phase fails after partial execution, inform the user about rollback options.
- On any unrecoverable error, release the cluster lock and inform the user.
- Never silently swallow errors -- always surface them to the user.

## Communication Style

- Be clear and professional.
- Explain technical concepts in accessible terms.
- Provide actionable recommendations.
- Summarize subagent results in customer-friendly language.
- Keep customers informed of progress at each step.
"""
