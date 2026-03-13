#!/bin/bash
# Deploy Redshift Modernization Agents via AWS CDK
#
# This script replaces the previous agentcore launch commands.
# All infrastructure (Lambda functions, Bedrock Agents, DynamoDB,
# Cognito) is now provisioned via CDK.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CDK_DIR="${SCRIPT_DIR}/cdk"

echo "Deploying Redshift Modernization Agents via CDK..."

# Install CDK dependencies if needed
if [ ! -d "${CDK_DIR}/.venv" ]; then
    echo "Installing CDK dependencies..."
    pip install -r "${SCRIPT_DIR}/requirements.txt" --quiet
fi

# Run CDK deploy from the cdk/ directory
echo "Running cdk deploy..."
cd "${CDK_DIR}"
cdk deploy --require-approval broadening "$@"

echo "Deployment complete!"
echo ""
echo "Set the following environment variables in your .env file:"
echo "  ORCHESTRATOR_AGENT_ID=<from CDK output OrchestratorAgentId>"
echo "  ORCHESTRATOR_AGENT_ALIAS_ID=<from CDK output OrchestratorAliasId>"
echo "  COGNITO_USER_POOL_ID=<from CDK output CognitoUserPoolId>"
echo "  COGNITO_APP_CLIENT_ID=<from CDK output CognitoAppClientId>"
echo "  COGNITO_IDENTITY_POOL_ID=<from CDK output CognitoIdentityPoolId>"
