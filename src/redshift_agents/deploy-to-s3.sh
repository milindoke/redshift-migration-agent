#!/bin/bash
# Deploy packaged agents to S3 (single customer account)

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

# Configuration — single customer account
AWS_PROFILE="${AWS_PROFILE:-default}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-}"
REGION="${AWS_REGION:-us-east-2}"

# Auto-detect account ID if not set
if [ -z "$AWS_ACCOUNT_ID" ]; then
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text)
fi

BUCKET="redshift-agents-${AWS_ACCOUNT_ID}"

echo ""
echo "Configuration:"
echo "  Account: ${AWS_ACCOUNT_ID}"
echo "  Bucket:  ${BUCKET}"
echo "  Region:  ${REGION}"
echo "  Profile: ${AWS_PROFILE}"
echo ""

# Verify credentials
echo -e "${BLUE}Verifying AWS credentials...${NC}"
if ! aws sts get-caller-identity --profile "$AWS_PROFILE" > /dev/null 2>&1; then
    echo -e "${RED}Error: AWS credentials are invalid or expired${NC}"
    echo "Please refresh credentials for profile: ${AWS_PROFILE}"
    exit 1
fi
echo -e "${GREEN}✓ Credentials valid${NC}"

echo ""
echo -e "${BLUE}Step 1: Create S3 bucket (if it doesn't exist)${NC}"

echo "Creating bucket: ${BUCKET}"
if aws s3 ls s3://${BUCKET} --profile "$AWS_PROFILE" 2>&1 | grep -q 'NoSuchBucket'; then
    aws s3 mb s3://${BUCKET} --region ${REGION} --profile "$AWS_PROFILE"
    echo -e "${GREEN}✓ Bucket created${NC}"
else
    echo -e "${GREEN}✓ Bucket already exists${NC}"
fi

echo ""
echo -e "${BLUE}Step 2: Upload all agent packages${NC}"

for agent in orchestrator assessment scoring architecture execution; do
    echo "Uploading ${agent}..."
    aws s3 cp packages/${agent}-deployment.zip \
        s3://${BUCKET}/${agent}/${agent}-deployment.zip \
        --profile "$AWS_PROFILE"
    echo -e "${GREEN}✓ ${agent} uploaded${NC}"
done

echo ""
echo -e "${GREEN}=================================================="
echo "All packages uploaded successfully!"
echo "==================================================${NC}"
echo ""
echo "S3 URIs:"
for agent in orchestrator assessment scoring architecture execution; do
    echo "  ${agent}: s3://${BUCKET}/${agent}/${agent}-deployment.zip"
done
echo ""
echo "Next steps:"
echo "1. Deploy via Bedrock AgentCore Console"
echo "2. Use the S3 URIs above"
echo "3. See docs/deployment-checklist.md for detailed instructions"
