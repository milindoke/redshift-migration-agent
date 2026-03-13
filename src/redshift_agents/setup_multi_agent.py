"""
Set up Bedrock Multi-Agent Collaboration for Redshift Modernization.

Creates a supervisor agent and associates the three subagents as collaborators
using the Bedrock Agent API. This replaces the hand-rolled orchestration with
Bedrock's native multi-agent collaboration feature.

The supervisor agent:
- Routes tasks to the appropriate collaborator based on workflow phase
- Manages the 3-phase workflow (assessment → architecture → execution)
- Enforces approval gates between phases via conversation flow

Prerequisites:
- Subagents deployed to Bedrock AgentCore via deploy-agentcore.sh
- Each subagent registered as a Bedrock Agent with an alias
- IAM role for the supervisor with bedrock:InvokeAgent permissions

Usage:
    python setup_multi_agent.py \\
        --supervisor-role-arn arn:aws:iam::ACCOUNT:role/redshift-supervisor \\
        --assessment-alias-arn arn:aws:bedrock:REGION:ACCOUNT:agent-alias/AGENT_ID/ALIAS_ID \\
        --architecture-alias-arn arn:aws:bedrock:REGION:ACCOUNT:agent-alias/AGENT_ID/ALIAS_ID \\
        --execution-alias-arn arn:aws:bedrock:REGION:ACCOUNT:agent-alias/AGENT_ID/ALIAS_ID
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import boto3

REGION = os.getenv("AWS_REGION", "us-east-2")
MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-20250514")


# ---------------------------------------------------------------------------
# Supervisor agent instruction
# ---------------------------------------------------------------------------

SUPERVISOR_INSTRUCTION = """You are the Redshift Modernization Supervisor Agent.

You coordinate a 3-phase workflow to migrate Redshift Provisioned clusters to Serverless.
You have three collaborator agents, each specialized for one phase.

## Collaborator Agents

1. **assessment-agent** — Analyzes the customer's Redshift cluster: configuration, CloudWatch
   metrics, WL
M queue contention. Delegate to this agent first.

2. **architecture-agent** — Designs the Serverless workgroup topology: WLM-to-workgroup
   mapping, RPU sizing (min 32), architecture pattern selection, cost estimates.
   Delegate to this agent after assessment is approved.

3. **execution-agent** — Executes the migration: creates namespace/workgroups, restores
   snapshots, sets up data sharing, migrates users, validates performance.
   Delegate to this agent after architecture is approved.

## Workflow Rules

### Phase 1: Assessment
- Collect cluster_id, region, and user_id from the customer.
- Delegate to assessment-agent.
- Present results to the customer.

### Gate 1: Approval Required
- Ask: "Based on the assessment, shall I proceed to architecture design?"
- Do NOT delegate to architecture-agent without explicit approval.

### Phase 2: Architecture
- Delegate to architecture-agent with the assessment results.
- Present the proposed architecture to the customer.

### Gate 2: Approval Required
- Ask: "Here is the proposed architecture. Shall I proceed to execution?"
- Do NOT delegate to execution-agent without explicit approval.

### Phase 3: Execution
- Delegate to execution-agent with the architecture spec.
- Present migration results to the customer.

## Identity Requirement
Every request MUST include a user_id. Reject requests without one.
Always pass user_id to every collaborator agent invocation.

## Communication Style
- Be clear and professional.
- Summarize collaborator results in customer-friendly language.
- Always surface errors — never silently swallow them.
"""


# ---------------------------------------------------------------------------
# Collaborator instructions
# ---------------------------------------------------------------------------

ASSESSMENT_COLLABORATION_INSTRUCTION = (
    "Delegate cluster analysis tasks to this agent. It discovers Redshift clusters, "
    "retrieves configuration and CloudWatch metrics, queries WLM queue configuration, "
    "and identifies contention problems. Use it for Phase 1 of the modernization workflow."
)

ARCHITECTURE_COLLABORATION_INSTRUCTION = (
    "Delegate architecture design tasks to this agent. It designs Serverless workgroup "
    "topology based on assessment results: WLM-to-workgroup mapping, RPU sizing (min 32), "
    "architecture pattern selection, cost estimates. Use it for Phase 2 after assessment approval."
)

EXECUTION_COLLABORATION_INSTRUCTION = (
    "Delegate migration execution tasks to this agent. It creates namespaces/workgroups, "
    "restores snapshots, sets up data sharing, generates user migration plans, validates "
    "performance, and defines rollback procedures. Use it for Phase 3 after architecture approval."
)


# ---------------------------------------------------------------------------
# Setup functions
# ---------------------------------------------------------------------------


def create_supervisor_agent(
    client,
    role_arn: str,
    agent_name: str = "redshift-modernization-supervisor",
) -> str:
    """Create the supervisor Bedrock Agent and return its agent ID."""
    print(f"Creating supervisor agent '{agent_name}'...")

    response = client.create_agent(
        agentName=agent_name,
        agentResourceRoleArn=role_arn,
        foundationModel=MODEL_ID,
        instruction=SUPERVISOR_INSTRUCTION,
        agentCollaboration="SUPERVISOR_ROUTER",
        idleSessionTTLInSeconds=1800,
    )

    agent_id = response["agent"]["agentId"]
    print(f"  Created agent: {agent_id}")
    return agent_id


def associate_collaborator(
    client,
    supervisor_agent_id: str,
    collaborator_alias_arn: str,
    collaborator_name: str,
    collaboration_instruction: str,
) -> str:
    """Associate a collaborator agent with the supervisor."""
    print(f"  Associating collaborator '{collaborator_name}'...")

    response = client.associate_agent_collaborator(
        agentId=supervisor_agent_id,
        agentVersion="DRAFT",
        agentDescriptor={"aliasArn": collaborator_alias_arn},
        collaboratorName=collaborator_name,
        collaborationInstruction=collaboration_instruction,
        relayConversationHistory="TO_COLLABORATOR",
    )

    collaborator_id = response["agentCollaborator"]["collaboratorId"]
    print(f"    Collaborator ID: {collaborator_id}")
    return collaborator_id


def prepare_agent(client, agent_id: str) -> None:
    """Prepare the agent for use."""
    print(f"  Preparing agent {agent_id}...")
    client.prepare_agent(agentId=agent_id)

    # Poll until prepared
    for _ in range(30):
        resp = client.get_agent(agentId=agent_id)
        status = resp["agent"]["agentStatus"]
        if status == "PREPARED":
            print(f"  Agent prepared.")
            return
        if status == "FAILED":
            raise RuntimeError(f"Agent preparation failed: {resp['agent'].get('failureReasons')}")
        time.sleep(2)

    raise TimeoutError("Agent preparation timed out")


def create_alias(client, agent_id: str, alias_name: str = "live") -> str:
    """Create an alias for the agent and return the alias ID."""
    print(f"  Creating alias '{alias_name}'...")
    response = client.create_agent_alias(
        agentId=agent_id,
        agentAliasName=alias_name,
    )
    alias_id = response["agentAlias"]["agentAliasId"]
    print(f"  Alias ID: {alias_id}")
    return alias_id


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Set up Bedrock Multi-Agent Collaboration for Redshift Modernization"
    )
    parser.add_argument(
        "--supervisor-role-arn", required=True,
        help="IAM role ARN for the supervisor agent",
    )
    parser.add_argument(
        "--assessment-alias-arn", required=True,
        help="Bedrock Agent alias ARN for the assessment collaborator",
    )
    parser.add_argument(
        "--architecture-alias-arn", required=True,
        help="Bedrock Agent alias ARN for the architecture collaborator",
    )
    parser.add_argument(
        "--execution-alias-arn", required=True,
        help="Bedrock Agent alias ARN for the execution collaborator",
    )
    parser.add_argument(
        "--region", default=REGION,
        help=f"AWS region (default: {REGION})",
    )
    parser.add_argument(
        "--agent-name", default="redshift-modernization-supervisor",
        help="Name for the supervisor agent",
    )

    args = parser.parse_args()

    client = boto3.client("bedrock-agent", region_name=args.region)

    # Step 1: Create supervisor agent
    agent_id = create_supervisor_agent(
        client, args.supervisor_role_arn, args.agent_name,
    )

    # Step 2: Associate collaborators
    associate_collaborator(
        client, agent_id,
        args.assessment_alias_arn,
        "assessment-agent",
        ASSESSMENT_COLLABORATION_INSTRUCTION,
    )
    associate_collaborator(
        client, agent_id,
        args.architecture_alias_arn,
        "architecture-agent",
        ARCHITECTURE_COLLABORATION_INSTRUCTION,
    )
    associate_collaborator(
        client, agent_id,
        args.execution_alias_arn,
        "execution-agent",
        EXECUTION_COLLABORATION_INSTRUCTION,
    )

    # Step 3: Prepare the supervisor
    prepare_agent(client, agent_id)

    # Step 4: Create alias
    alias_id = create_alias(client, agent_id)

    print()
    print("=" * 60)
    print("Multi-agent collaboration setup complete!")
    print(f"  Supervisor Agent ID: {agent_id}")
    print(f"  Supervisor Alias ID: {alias_id}")
    print()
    print("Set these in your environment:")
    print(f"  export ORCHESTRATOR_AGENT_ID={agent_id}")
    print(f"  export ORCHESTRATOR_AGENT_ALIAS_ID={alias_id}")
    print()
    print("Then launch the chat UI:")
    print("  streamlit run ui/app.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
