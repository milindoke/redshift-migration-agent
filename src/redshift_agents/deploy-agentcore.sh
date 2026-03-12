#!/bin/bash
# Deploy Redshift Modernization Agents to Amazon Bedrock AgentCore
set -e

REGION="${AWS_REGION:-us-east-2}"

echo "Deploying Redshift Modernization Agents via agentcore launch..."

# Deploy orchestrator
echo "[1/4] Deploying orchestrator..."
agentcore launch --name redshift-orchestrator --entry orchestrator/orchestrator.py --region "$REGION"

# Deploy assessment agent
echo "[2/4] Deploying assessment agent..."
agentcore launch --name redshift-assessment --entry subagents/assessment.py --region "$REGION"

# Deploy architecture agent
echo "[3/4] Deploying architecture agent..."
agentcore launch --name redshift-architecture --entry subagents/architecture.py --region "$REGION"

# Deploy execution agent
echo "[4/4] Deploying execution agent..."
agentcore launch --name redshift-execution --entry subagents/execution.py --region "$REGION"

echo "All agents deployed successfully!"
