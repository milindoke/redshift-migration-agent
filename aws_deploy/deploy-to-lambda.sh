#!/bin/bash
# Deploy Redshift Migration Agent to AWS Lambda

set -e

echo "🚀 Deploying Redshift Migration Agent to AWS Lambda"
echo "===================================================="

# Configuration
AWS_REGION="us-east-2"
FUNCTION_NAME="redshift-migration-agent"
ROLE_NAME="RedshiftAgentLambdaRole"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${YELLOW}Step 1: Creating Lambda Deployment Package${NC}"

# Activate venv if it exists
if [ -d "venv" ]; then
  source venv/bin/activate
  echo "Using virtual environment"
else
  echo "Error: Virtual environment not found. Run ./deploy_agent.sh first"
  exit 1
fi

# Create temp directory
rm -rf lambda_package lambda_deployment.zip
mkdir lambda_package

# Install dependencies
pip install -r requirements-agent.txt -t lambda_package/ --quiet

# Copy source code
cp -r src/ lambda_package/
cp redshift_agent.py lambda_package/
cp lambda_handler.py lambda_package/

# Create zip
cd lambda_package
zip -r ../lambda_deployment.zip . -q
cd ..

echo -e "${GREEN}✓ Deployment package created ($(du -h lambda_deployment.zip | cut -f1))${NC}"

echo ""
echo -e "${YELLOW}Step 2: Creating IAM Role${NC}"

# Check if role exists
aws iam get-role --role-name $ROLE_NAME 2>/dev/null || \
aws iam create-role \
  --role-name $ROLE_NAME \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policies
aws iam attach-role-policy \
  --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null || true

aws iam put-role-policy \
  --role-name $ROLE_NAME \
  --policy-name RedshiftAgentPolicy \
  --policy-document file://aws_deploy/task-role-policy.json

echo -e "${GREEN}✓ IAM role configured${NC}"

# Wait for role to propagate
echo "Waiting for IAM role to propagate..."
sleep 10

echo ""
echo -e "${YELLOW}Step 3: Uploading to S3 and Creating Lambda Function${NC}"

# Create S3 bucket for deployment
BUCKET_NAME="redshift-agent-deployment-$(date +%s)"
aws s3 mb s3://$BUCKET_NAME --region $AWS_REGION

# Upload zip to S3
aws s3 cp lambda_deployment.zip s3://$BUCKET_NAME/lambda_deployment.zip

# Get role ARN
ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)

# Check if function exists
FUNCTION_EXISTS=$(aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION 2>/dev/null || echo "")

if [ -z "$FUNCTION_EXISTS" ]; then
  echo "Creating new Lambda function from S3..."
  aws lambda create-function \
    --function-name $FUNCTION_NAME \
    --runtime python3.11 \
    --role $ROLE_ARN \
    --handler lambda_handler.lambda_handler \
    --code S3Bucket=$BUCKET_NAME,S3Key=lambda_deployment.zip \
    --timeout 300 \
    --memory-size 2048 \
    --region $AWS_REGION \
    --ephemeral-storage Size=1024
else
  echo "Updating existing Lambda function from S3..."
  aws lambda update-function-code \
    --function-name $FUNCTION_NAME \
    --s3-bucket $BUCKET_NAME \
    --s3-key lambda_deployment.zip \
    --region $AWS_REGION
  
  aws lambda update-function-configuration \
    --function-name $FUNCTION_NAME \
    --timeout 300 \
    --memory-size 2048 \
    --region $AWS_REGION \
    --ephemeral-storage Size=1024
fi

echo -e "${GREEN}✓ Lambda function deployed${NC}"

echo ""
echo -e "${YELLOW}Step 4: Creating Function URL${NC}"

# Create function URL for easy access
aws lambda create-function-url-config \
  --function-name $FUNCTION_NAME \
  --auth-type NONE \
  --region $AWS_REGION 2>/dev/null || \
echo "Function URL already exists"

# Add permission for public access
aws lambda add-permission \
  --function-name $FUNCTION_NAME \
  --statement-id FunctionURLAllowPublicAccess \
  --action lambda:InvokeFunctionUrl \
  --principal "*" \
  --function-url-auth-type NONE \
  --region $AWS_REGION 2>/dev/null || \
echo "Permission already exists"

# Get function URL
FUNCTION_URL=$(aws lambda get-function-url-config \
  --function-name $FUNCTION_NAME \
  --region $AWS_REGION \
  --query 'FunctionUrl' \
  --output text)

echo -e "${GREEN}✓ Function URL configured${NC}"

# Cleanup
rm -rf lambda_package lambda_deployment.zip

echo ""
echo "=========================================================="
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo "=========================================================="
echo ""
echo "Function URL: $FUNCTION_URL"
echo ""
echo "Test with:"
echo "  curl -X POST $FUNCTION_URL \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"message\": \"List my Redshift clusters\"}'"
echo ""
echo "View logs:"
echo "  aws logs tail /aws/lambda/$FUNCTION_NAME --follow --region $AWS_REGION"
echo ""
echo "Estimated cost: ~\$0-20/month (depending on usage)"
