#!/bin/bash

# Script to add missing EC2 permissions to the Lambda execution role

set -e

REGION="us-east-2"
POLICY_NAME="RedshiftAgentExecutionPolicy"

echo "🔧 Adding EC2 permissions to Lambda execution role..."
echo ""

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region $REGION)

if [ -z "$ACCOUNT_ID" ]; then
    echo "❌ Failed to get AWS account ID. Please refresh your credentials:"
    echo "   aws configure"
    exit 1
fi

echo "✅ AWS Account: $ACCOUNT_ID"
echo ""

# Get the policy ARN
POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}"

echo "📋 Policy ARN: $POLICY_ARN"
echo ""

# Get current policy version
CURRENT_VERSION=$(aws iam get-policy --policy-arn $POLICY_ARN --region $REGION --query 'Policy.DefaultVersionId' --output text)

echo "📌 Current policy version: $CURRENT_VERSION"
echo ""

# Get current policy document
echo "📄 Fetching current policy document..."
CURRENT_POLICY=$(aws iam get-policy-version \
  --policy-arn $POLICY_ARN \
  --version-id $CURRENT_VERSION \
  --region $REGION \
  --query 'PolicyVersion.Document' \
  --output json)

# Create updated policy with new EC2 permissions
echo "✏️  Creating updated policy document..."

cat > /tmp/updated_policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "redshift:DescribeClusters",
        "redshift:DescribeClusterParameters",
        "redshift:DescribeClusterParameterGroups",
        "redshift:DescribeClusterSnapshots",
        "redshift:DescribeEventSubscriptions",
        "redshift:DescribeLoggingStatus",
        "redshift:DescribeTags",
        "redshift:CreateClusterSnapshot",
        "redshift:ModifyCluster"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "redshift-serverless:GetNamespace",
        "redshift-serverless:GetWorkgroup",
        "redshift-serverless:ListNamespaces",
        "redshift-serverless:ListWorkgroups",
        "redshift-serverless:CreateNamespace",
        "redshift-serverless:CreateWorkgroup",
        "redshift-serverless:UpdateNamespace",
        "redshift-serverless:UpdateWorkgroup",
        "redshift-serverless:RestoreFromSnapshot"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeAccountAttributes",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeAddresses",
        "ec2:DescribeInternetGateways"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:ListRoles",
        "iam:GetRole",
        "iam:PassRole"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "events:DescribeRule",
        "events:ListRules",
        "events:PutRule",
        "events:PutTargets"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "scheduler:GetSchedule",
        "scheduler:ListSchedules",
        "scheduler:CreateSchedule"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create new policy version
echo "🔄 Creating new policy version..."
NEW_VERSION=$(aws iam create-policy-version \
  --policy-arn $POLICY_ARN \
  --policy-document file:///tmp/updated_policy.json \
  --set-as-default \
  --region $REGION \
  --query 'PolicyVersion.VersionId' \
  --output text)

if [ $? -eq 0 ]; then
    echo "✅ Successfully created new policy version: $NEW_VERSION"
    echo ""
    echo "📋 Added EC2 permissions:"
    echo "   • ec2:DescribeAccountAttributes"
    echo "   • ec2:DescribeVpcs"
    echo "   • ec2:DescribeSubnets"
    echo "   • ec2:DescribeSecurityGroups"
    echo "   • ec2:DescribeAddresses"
    echo "   • ec2:DescribeInternetGateways"
    echo ""
    echo "🎉 Permissions updated successfully!"
else
    echo "❌ Failed to create new policy version"
    exit 1
fi

# Clean up
rm -f /tmp/updated_policy.json

echo ""
echo "✅ Done! The Lambda function now has the required EC2 permissions."
