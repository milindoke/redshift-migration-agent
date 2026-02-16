#!/bin/bash

# Script to check Lambda function logs for errors

FUNCTION_NAME="redshift-migration-agent"
REGION="us-east-2"

echo "🔍 Checking CloudWatch logs for $FUNCTION_NAME..."
echo ""

# Get the latest log stream
echo "📋 Latest log entries (last 5 minutes):"
echo "========================================"
aws logs tail /aws/lambda/$FUNCTION_NAME \
  --region $REGION \
  --since 5m \
  --format short

echo ""
echo "========================================"
echo ""

# Get error logs specifically
echo "❌ Error logs (last 10 minutes):"
echo "========================================"
aws logs tail /aws/lambda/$FUNCTION_NAME \
  --region $REGION \
  --since 10m \
  --filter-pattern "ERROR" \
  --format short

echo ""
echo "========================================"
echo ""

# Get the most recent invocation errors
echo "🔥 Recent exceptions:"
echo "========================================"
aws logs tail /aws/lambda/$FUNCTION_NAME \
  --region $REGION \
  --since 10m \
  --filter-pattern "Traceback" \
  --format short

echo ""
echo "Done! ✅"
