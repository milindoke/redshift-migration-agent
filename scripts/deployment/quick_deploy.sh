#!/bin/bash

# Quick Deploy Script for Redshift Migration Agent
# This script deploys the agent to your AWS account

set -e

echo "🚀 Redshift Migration Agent - Quick Deploy"
echo "=========================================="
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first:"
    echo "   https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# Check if SAM CLI is installed
if ! command -v sam &> /dev/null; then
    echo "❌ SAM CLI not found. Please install it first:"
    echo "   https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
    exit 1
fi

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
if [ -z "$ACCOUNT_ID" ]; then
    echo "❌ Unable to get AWS account ID. Please configure AWS credentials:"
    echo "   aws configure"
    exit 1
fi

echo "✅ AWS Account: $ACCOUNT_ID"
echo ""

# Build the application
echo "📦 Building application..."
sam build

if [ $? -ne 0 ]; then
    echo "❌ Build failed"
    exit 1
fi

echo "✅ Build complete"
echo ""

# Deploy the application
echo "🚀 Deploying to AWS..."
echo ""
echo "You'll be asked a few questions:"
echo "  - Stack Name: Press Enter for default (redshift-migration-agent)"
echo "  - AWS Region: Enter your preferred region (e.g., us-east-2)"
echo "  - Confirm changes: Y"
echo "  - Allow SAM CLI IAM role creation: Y"
echo "  - Save arguments to config: Y"
echo ""

sam deploy --guided

if [ $? -ne 0 ]; then
    echo "❌ Deployment failed"
    exit 1
fi

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Test the agent:"
echo "   aws lambda invoke \\"
echo "     --function-name redshift-migration-agent \\"
echo "     --cli-binary-format raw-in-base64-out \\"
echo "     --payload '{\"message\":\"List my Redshift clusters\"}' \\"
echo "     response.json"
echo ""
echo "   cat response.json"
echo ""
echo "2. (Optional) Set up persistent memory:"
echo "   python scripts/setup_memory.py --region us-east-2"
echo ""
echo "3. Use with session_id for long-running migrations:"
echo "   aws lambda invoke \\"
echo "     --function-name redshift-migration-agent \\"
echo "     --payload '{\"message\":\"Start migration\",\"session_id\":\"my-migration\"}' \\"
echo "     response.json"
echo ""
echo "🎉 Your agent is ready to use!"
