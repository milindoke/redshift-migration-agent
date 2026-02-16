#!/bin/bash
# Setup secure access to Redshift Migration Agent Lambda

set -e

AWS_REGION="us-east-2"
FUNCTION_NAME="redshift-migration-agent"
POLICY_NAME="RedshiftAgentInvokePolicy"
GROUP_NAME="RedshiftAgentUsers"

echo "🔒 Setting up secure access to Redshift Migration Agent"
echo "========================================================"

echo ""
echo "Step 1: Creating IAM policy for Lambda invocation"

# Create policy that allows invoking the Lambda function
POLICY_ARN=$(aws iam create-policy \
  --policy-name $POLICY_NAME \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": "lambda:InvokeFunction",
        "Resource": "arn:aws:lambda:'$AWS_REGION':${AWS::AccountId}:function:'$FUNCTION_NAME'"
      }
    ]
  }' \
  --query 'Policy.Arn' \
  --output text 2>/dev/null || \
  aws iam list-policies --query "Policies[?PolicyName=='$POLICY_NAME'].Arn" --output text)

echo "✓ Policy created: $POLICY_ARN"

echo ""
echo "Step 2: Creating IAM group for authorized users"

aws iam create-group --group-name $GROUP_NAME 2>/dev/null || echo "Group already exists"

# Attach policy to group
aws iam attach-group-policy \
  --group-name $GROUP_NAME \
  --policy-arn $POLICY_ARN

echo "✓ Group created: $GROUP_NAME"

echo ""
echo "Step 3: Creating example IAM user"

USER_NAME="redshift-agent-user"
aws iam create-user --user-name $USER_NAME 2>/dev/null || echo "User already exists"

# Add user to group
aws iam add-user-to-group \
  --user-name $USER_NAME \
  --group-name $GROUP_NAME

echo "✓ User created: $USER_NAME"

echo ""
echo "Step 4: Creating access keys"

# Create access key
ACCESS_KEY=$(aws iam create-access-key --user-name $USER_NAME 2>/dev/null || echo "")

if [ -n "$ACCESS_KEY" ]; then
  ACCESS_KEY_ID=$(echo $ACCESS_KEY | jq -r '.AccessKey.AccessKeyId')
  SECRET_ACCESS_KEY=$(echo $ACCESS_KEY | jq -r '.AccessKey.SecretAccessKey')
  
  echo "✓ Access keys created"
  echo ""
  echo "Save these credentials securely:"
  echo "================================"
  echo "AWS_ACCESS_KEY_ID=$ACCESS_KEY_ID"
  echo "AWS_SECRET_ACCESS_KEY=$SECRET_ACCESS_KEY"
  echo ""
  
  # Save to file
  cat > .agent-credentials << EOF
# Redshift Migration Agent Credentials
# Add these to your environment or use with AWS CLI

export AWS_ACCESS_KEY_ID=$ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=$SECRET_ACCESS_KEY
export AWS_REGION=$AWS_REGION
EOF
  
  echo "Credentials saved to: .agent-credentials"
  echo "Load with: source .agent-credentials"
else
  echo "⚠️  Access key already exists for this user"
  echo "To create new keys, delete existing ones first:"
  echo "  aws iam list-access-keys --user-name $USER_NAME"
  echo "  aws iam delete-access-key --user-name $USER_NAME --access-key-id <KEY_ID>"
fi

echo ""
echo "========================================================"
echo "✅ Secure access configured!"
echo "========================================================"
echo ""
echo "To invoke the Lambda function:"
echo ""
echo "1. Configure AWS CLI with the credentials above:"
echo "   aws configure"
echo ""
echo "2. Invoke the function:"
echo "   aws lambda invoke \\"
echo "     --function-name $FUNCTION_NAME \\"
echo "     --cli-binary-format raw-in-base64-out \\"
echo "     --payload '{\"message\":\"List my clusters\"}' \\"
echo "     --region $AWS_REGION \\"
echo "     response.json"
echo ""
echo "3. Or use the Python client (see examples/secure_client.py)"
echo ""
echo "To add more users:"
echo "  aws iam create-user --user-name <username>"
echo "  aws iam add-user-to-group --user-name <username> --group-name $GROUP_NAME"
echo "  aws iam create-access-key --user-name <username>"
