#!/bin/bash

# Push all container images to ECR (single customer account)

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration — single customer account
AWS_PROFILE="${AWS_PROFILE:-default}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-}"
REGION="${AWS_REGION:-us-east-2}"

echo -e "${BLUE}[INFO]${NC} Pushing images to ECR..."
echo

# Auto-detect account ID if not set
if [ -z "$AWS_ACCOUNT_ID" ]; then
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text)
fi
echo -e "${BLUE}[INFO]${NC} Account: $AWS_ACCOUNT_ID"

# Create ECR repositories
echo -e "${BLUE}[STEP]${NC} Creating ECR repositories..."

for agent in orchestrator assessment scoring architecture execution; do
    aws ecr create-repository \
        --repository-name redshift-${agent} \
        --region $REGION \
        --profile "$AWS_PROFILE" \
        2>/dev/null || echo -e "${YELLOW}[WARN]${NC} Repository redshift-${agent} may already exist"
done

echo -e "${GREEN}✓${NC} ECR repositories ready"
echo

# Authenticate
echo -e "${BLUE}[STEP]${NC} Authenticating Finch to ECR..."
aws ecr get-login-password \
    --region $REGION \
    --profile "$AWS_PROFILE" | \
    finch login --username AWS --password-stdin \
    $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Tag and push all agents
echo -e "${BLUE}[STEP]${NC} Pushing all agent images..."

for agent in orchestrator assessment scoring architecture execution; do
    echo "Tagging and pushing redshift-${agent}..."

    finch tag redshift-${agent}:latest \
        $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-${agent}:latest

    finch push $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-${agent}:latest

    echo -e "${GREEN}✓${NC} Pushed redshift-${agent}"
done

echo
echo -e "${GREEN}[SUCCESS]${NC} All images pushed to ECR! 🎉"
echo
echo "=============================================="
echo "ECR Image URIs (Account $AWS_ACCOUNT_ID):"
echo "=============================================="
echo
for agent in orchestrator assessment scoring architecture execution; do
    echo "$AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-${agent}:latest"
done
echo
echo "=============================================="
echo "Next Steps:"
echo "=============================================="
echo
echo "1. Deploy to Bedrock AgentCore via Console:"
echo "   - Open AWS Bedrock Console → AgentCore"
echo "   - Create Agent for each image URI above"
echo "   - Set environment variables"
echo "   - Deploy"
echo
echo "2. Register agents with ATX Agent Registry"
echo
echo "3. Test deployment"
