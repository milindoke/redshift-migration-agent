#!/bin/bash

# Quick fix script for Lambda issues

set -e

FUNCTION_NAME="redshift-migration-agent"
REGION="us-east-2"

echo "🔧 Lambda Fix Script"
echo "===================="
echo ""

# Check credentials
echo "1️⃣ Checking AWS credentials..."
if aws sts get-caller-identity --region $REGION > /dev/null 2>&1; then
    echo "   ✅ Credentials valid"
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    echo "   Account: $ACCOUNT_ID"
else
    echo "   ❌ Credentials expired or invalid"
    echo "   Run: aws configure"
    exit 1
fi
echo ""

# Check if function exists
echo "2️⃣ Checking Lambda function..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION > /dev/null 2>&1; then
    echo "   ✅ Function exists"
else
    echo "   ❌ Function not found"
    echo "   Deploy first: sam build && sam deploy"
    exit 1
fi
echo ""

# Check Bedrock access
echo "3️⃣ Checking Bedrock model access..."
if aws bedrock list-foundation-models --region $REGION --query 'modelSummaries[?contains(modelId, `claude-sonnet-4`)].modelId' --output text 2>/dev/null | grep -q "claude"; then
    echo "   ✅ Bedrock models accessible"
else
    echo "   ⚠️  Cannot verify Bedrock access"
    echo "   Enable at: https://console.aws.amazon.com/bedrock"
fi
echo ""

# Get recent logs
echo "4️⃣ Checking recent logs for errors..."
echo "   (Last 5 minutes)"
echo "   ----------------------------------------"
aws logs tail /aws/lambda/$FUNCTION_NAME --region $REGION --since 5m --format short 2>/dev/null || echo "   No recent logs found"
echo "   ----------------------------------------"
echo ""

# Check environment variables
echo "5️⃣ Checking Lambda configuration..."
MODEL_ID=$(aws lambda get-function-configuration \
  --function-name $FUNCTION_NAME \
  --region $REGION \
  --query 'Environment.Variables.BEDROCK_MODEL_ID' \
  --output text 2>/dev/null || echo "Not set")
echo "   Model ID: $MODEL_ID"

MEMORY=$(aws lambda get-function-configuration \
  --function-name $FUNCTION_NAME \
  --region $REGION \
  --query 'MemorySize' \
  --output text)
echo "   Memory: ${MEMORY}MB"

TIMEOUT=$(aws lambda get-function-configuration \
  --function-name $FUNCTION_NAME \
  --region $REGION \
  --query 'Timeout' \
  --output text)
echo "   Timeout: ${TIMEOUT}s"
echo ""

# Test invocation
echo "6️⃣ Testing Lambda invocation..."
echo "   Sending test message..."
aws lambda invoke \
  --function-name $FUNCTION_NAME \
  --region $REGION \
  --cli-binary-format raw-in-base64-out \
  --payload '{"message":"Hello, are you working?"}' \
  test_response.json > /dev/null 2>&1

if [ -f test_response.json ]; then
    if grep -q "error" test_response.json; then
        echo "   ❌ Error in response:"
        cat test_response.json | jq . 2>/dev/null || cat test_response.json
    elif grep -q "response" test_response.json; then
        echo "   ✅ Function working!"
        echo "   Response:"
        cat test_response.json | jq -r '.response' 2>/dev/null | head -n 3
    else
        echo "   ⚠️  Unexpected response:"
        cat test_response.json
    fi
    rm test_response.json
else
    echo "   ❌ No response file created"
fi
echo ""

# Recommendations
echo "📋 Recommendations:"
echo "===================="

# Check if model ID is set
if [ "$MODEL_ID" == "Not set" ] || [ "$MODEL_ID" == "None" ]; then
    echo "⚠️  Set Bedrock model ID:"
    echo "   aws lambda update-function-configuration \\"
    echo "     --function-name $FUNCTION_NAME \\"
    echo "     --region $REGION \\"
    echo "     --environment Variables={BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0}"
    echo ""
fi

# Check memory
if [ "$MEMORY" -lt 2048 ]; then
    echo "⚠️  Increase memory (recommended 2048MB+):"
    echo "   aws lambda update-function-configuration \\"
    echo "     --function-name $FUNCTION_NAME \\"
    echo "     --region $REGION \\"
    echo "     --memory-size 2048"
    echo ""
fi

# Check timeout
if [ "$TIMEOUT" -lt 300 ]; then
    echo "⚠️  Increase timeout (recommended 300s+):"
    echo "   aws lambda update-function-configuration \\"
    echo "     --function-name $FUNCTION_NAME \\"
    echo "     --region $REGION \\"
    echo "     --timeout 300"
    echo ""
fi

echo "✅ Diagnosis complete!"
echo ""
echo "For detailed logs, run:"
echo "  ./check_lambda_logs.sh"
echo ""
echo "To redeploy:"
echo "  sam build --use-container && sam deploy"
