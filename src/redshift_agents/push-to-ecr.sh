#!/bin/bash

# Push container images to ECR

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SERVICE_ACCOUNT_PROFILE="service-account"
CUSTOMER_ACCOUNT_PROFILE="customer-account"
SERVICE_ACCOUNT_ID="497316421912"
CUSTOMER_ACCOUNT_ID="188199011335"
REGION="us-east-2"

echo -e "${BLUE}[INFO]${NC} Pushing images to ECR..."
echo

# Create ECR repositories
echo -e "${BLUE}[STEP]${NC} Creating ECR repositories..."

# Service account - orchestrator
echo "Creating orchestrator repository..."
aws ecr create-repository \
    --repository-name redshift-orchestrator \
    --region $REGION \
    --profile $SERVICE_ACCOUNT_PROFILE \
    2>/dev/null || echo "Repository may already exist"

# Customer account - subagents
echo "Creating subagent repositories..."
for agent in assessment scoring architecture execution; do
    aws ecr create-repository \
        --repository-name redshift-${agent} \
        --region $REGION \
        --profile $CUSTOMER_ACCOUNT_PROFILE \
        2>/dev/null || echo "Repository redshift-${agent} may already exist"
done

echo -e "${GREEN}✓${NC} ECR repositories ready"
echo

# Push orchestrator
echo -e "${BLUE}[STEP]${NC} Pushing orchestrator to service account ECR..."

# Authenticate
echo "Authenticating Finch to ECR..."
aws ecr get-login-password \
    --region $REGION \
    --profile $SERVICE_ACCOUNT_PROFILE | \
    finch login --username AWS --password-stdin \
    $SERVICE_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Tag
echo "Tagging orchestrator..."
finch tag redshift-orchestrator:latest \
    $SERVICE_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-orchestrator:latest

# Push
echo "Pushing orchestrator (this may take 5 minutes)..."
finch push $SERVICE_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-orchestrator:latest

echo -e "${GREEN}✓${NC} Orchestrator pushed"
echo "Image URI: $SERVICE_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-orchestrator:latest"
echo

# Push subagents
echo -e "${BLUE}[STEP]${NC} Pushing subagents to customer account ECR..."

# Authenticate
echo "Authenticating Finch to ECR..."
aws ecr get-login-password \
    --region $REGION \
    --profile $CUSTOMER_ACCOUNT_PROFILE | \
    finch login --username AWS --password-stdin \
    $CUSTOMER_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Tag and push each subagent
for agent in assessment scoring architecture execution; do
    echo "Tagging and pushing redshift-${agent}..."
    
    finch tag redshift-${agent}:latest \
        $CUSTOMER_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-${agent}:latest
    
    finch push $CUSTOMER_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-${agent}:latest
    
    echo -e "${GREEN}✓${NC} Pushed redshift-${agent}"
done

echo
echo -e "${GREEN}[SUCCESS]${NC} All images pushed to ECR! 🎉"
echo
echo "=============================================="
echo "ECR Image URIs:"
echo "=============================================="
echo
echo "Orchestrator (Service Account $SERVICE_ACCOUNT_ID):"
echo "$SERVICE_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-orchestrator:latest"
echo
echo "Subagents (Customer Account $CUSTOMER_ACCOUNT_ID):"
echo "$CUSTOMER_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-assessment:latest"
echo "$CUSTOMER_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-scoring:latest"
echo "$CUSTOMER_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-architecture:latest"
echo "$CUSTOMER_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-execution:latest"
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
echo
echo "See BUILD_SUCCESS.md for detailed instructions."
