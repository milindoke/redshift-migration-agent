#!/bin/bash

# Quick redeploy script to fix the pydantic_core issue

set -e

echo "🔄 Redeploying Lambda with proper dependencies..."
echo "================================================"
echo ""

# Check if SAM is installed
if ! command -v sam &> /dev/null; then
    echo "❌ SAM CLI not found. Install it first:"
    echo "   brew install aws-sam-cli"
    exit 1
fi

# Clean previous build
echo "1️⃣ Cleaning previous build..."
rm -rf .aws-sam
echo "   ✅ Clean complete"
echo ""

# Build with container (ensures proper compilation for Lambda)
echo "2️⃣ Building with container (this may take a few minutes)..."
echo "   This ensures all dependencies are compiled for Lambda runtime"
sam build --use-container

if [ $? -ne 0 ]; then
    echo "   ❌ Build failed"
    exit 1
fi
echo "   ✅ Build complete"
echo ""

# Deploy
echo "3️⃣ Deploying to AWS..."
sam deploy

if [ $? -ne 0 ]; then
    echo "   ❌ Deploy failed"
    exit 1
fi
echo "   ✅ Deploy complete"
echo ""

# Wait a moment for deployment to settle
echo "⏳ Waiting 5 seconds for deployment to settle..."
sleep 5
echo ""

# Test the function
echo "4️⃣ Testing the function..."
aws lambda invoke \
  --function-name redshift-migration-agent \
  --region us-east-2 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"message":"Hello, are you working now?"}' \
  test_response.json > /dev/null 2>&1

if [ -f test_response.json ]; then
    if grep -q '"response"' test_response.json; then
        echo "   ✅ Function is working!"
        echo ""
        echo "   Response:"
        cat test_response.json | jq -r '.response' 2>/dev/null | head -n 5
    else
        echo "   ⚠️  Response received but may have errors:"
        cat test_response.json | jq . 2>/dev/null || cat test_response.json
    fi
    rm test_response.json
else
    echo "   ❌ No response received"
fi
echo ""

echo "================================================"
echo "✅ Redeploy complete!"
echo ""
echo "Test your agent:"
echo "  aws lambda invoke \\"
echo "    --function-name redshift-migration-agent \\"
echo "    --region us-east-2 \\"
echo "    --cli-binary-format raw-in-base64-out \\"
echo "    --payload '{\"message\":\"List my Redshift clusters\"}' \\"
echo "    response.json"
echo ""
echo "  cat response.json"
