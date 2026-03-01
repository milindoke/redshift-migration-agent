#!/bin/bash
# Deploy packaged agents to S3

set -e

echo "Deploying Redshift Modernization Agents to S3..."
echo "=================================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Check if packages exist
if [ ! -d "packages" ]; then
    echo -e "${RED}Error: packages/ directory not found${NC}"
    echo "Run ./package-all.sh first"
    exit 1
fi

# Service Account Configuration
SERVICE_ACCOUNT_ID="497316421912"
SERVICE_BUCKET="redshift-agents-${SERVICE_ACCOUNT_ID}"
SERVICE_REGION="us-east-2"
SERVICE_PROFILE="service-account"

# Customer Account Configuration
CUSTOMER_ACCOUNT_ID="188199011335"
CUSTOMER_BUCKET="redshift-agents-${CUSTOMER_ACCOUNT_ID}"
CUSTOMER_REGION="us-east-2"
CUSTOMER_PROFILE="customer-account"

echo ""
echo "Configuration:"
echo "  Service Account: ${SERVICE_ACCOUNT_ID}"
echo "  Service Bucket: ${SERVICE_BUCKET}"
echo "  Customer Account: ${CUSTOMER_ACCOUNT_ID}"
echo "  Customer Bucket: ${CUSTOMER_BUCKET}"
echo ""

# Verify credentials
echo -e "${BLUE}Verifying AWS credentials...${NC}"

echo "Checking service account credentials..."
if ! aws sts get-caller-identity --profile ${SERVICE_PROFILE} > /dev/null 2>&1; then
    echo -e "${RED}Error: Service account credentials are invalid or expired${NC}"
    echo "Please refresh credentials for profile: ${SERVICE_PROFILE}"
    exit 1
fi
echo -e "${GREEN}✓ Service account credentials valid${NC}"

echo "Checking customer account credentials..."
if ! aws sts get-caller-identity --profile ${CUSTOMER_PROFILE} > /dev/null 2>&1; then
    echo -e "${RED}Error: Customer account credentials are invalid or expired${NC}"
    echo "Please refresh credentials for profile: ${CUSTOMER_PROFILE}"
    exit 1
fi
echo -e "${GREEN}✓ Customer account credentials valid${NC}"

echo ""
echo -e "${BLUE}Step 1: Create S3 buckets (if they don't exist)${NC}"

# Create service account bucket
echo "Creating service account bucket: ${SERVICE_BUCKET}"
if aws s3 ls s3://${SERVICE_BUCKET} --profile ${SERVICE_PROFILE} 2>&1 | grep -q 'NoSuchBucket'; then
    aws s3 mb s3://${SERVICE_BUCKET} --region ${SERVICE_REGION} --profile ${SERVICE_PROFILE}
    echo -e "${GREEN}✓ Service bucket created${NC}"
else
    echo -e "${GREEN}✓ Service bucket already exists${NC}"
fi

# Create customer account bucket
echo "Creating customer account bucket: ${CUSTOMER_BUCKET}"
if aws s3 ls s3://${CUSTOMER_BUCKET} --profile ${CUSTOMER_PROFILE} 2>&1 | grep -q 'NoSuchBucket'; then
    aws s3 mb s3://${CUSTOMER_BUCKET} --region ${CUSTOMER_REGION} --profile ${CUSTOMER_PROFILE}
    echo -e "${GREEN}✓ Customer bucket created${NC}"
else
    echo -e "${GREEN}✓ Customer bucket already exists${NC}"
fi

echo ""
echo -e "${BLUE}Step 2: Upload orchestrator to service account${NC}"
aws s3 cp packages/orchestrator-deployment.zip \
    s3://${SERVICE_BUCKET}/orchestrator/orchestrator-deployment.zip \
    --profile ${SERVICE_PROFILE}
echo -e "${GREEN}✓ Orchestrator uploaded${NC}"

echo ""
echo -e "${BLUE}Step 3: Upload subagents to customer account${NC}"

for agent in assessment scoring architecture execution; do
    echo "Uploading ${agent} subagent..."
    aws s3 cp packages/${agent}-deployment.zip \
        s3://${CUSTOMER_BUCKET}/${agent}/${agent}-deployment.zip \
        --profile ${CUSTOMER_PROFILE}
    echo -e "${GREEN}✓ ${agent} subagent uploaded${NC}"
done

echo ""
echo -e "${GREEN}=================================================="
echo "All packages uploaded successfully!"
echo "==================================================${NC}"
echo ""
echo "S3 URIs:"
echo "  Orchestrator: s3://${SERVICE_BUCKET}/orchestrator/orchestrator-deployment.zip"
echo "  Assessment:   s3://${CUSTOMER_BUCKET}/assessment/assessment-deployment.zip"
echo "  Scoring:      s3://${CUSTOMER_BUCKET}/scoring/scoring-deployment.zip"
echo "  Architecture: s3://${CUSTOMER_BUCKET}/architecture/architecture-deployment.zip"
echo "  Execution:    s3://${CUSTOMER_BUCKET}/execution/execution-deployment.zip"
echo ""
echo "Next steps:"
echo "1. Deploy via Bedrock AgentCore Console"
echo "2. Use the S3 URIs above"
echo "3. See README.md for detailed deployment instructions"
