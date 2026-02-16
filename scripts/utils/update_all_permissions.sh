#!/bin/bash

# Script to add all required permissions for workgroup creation and snapshot restoration

set -e

REGION="us-east-2"
POLICY_NAME="RedshiftAgentExecutionPolicy"

echo "🔧 Adding comprehensive permissions for Redshift Serverless operations..."
echo ""

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region $REGION 2>/dev/null)

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

# Check if policy exists
if ! aws iam get-policy --policy-arn $POLICY_ARN --region $REGION > /dev/null 2>&1; then
    echo "❌ Policy not found: $POLICY_NAME"
    echo "   Please deploy the agent first: ./deploy"
    exit 1
fi

# Get current policy version
CURRENT_VERSION=$(aws iam get-policy --policy-arn $POLICY_ARN --region $REGION --query 'Policy.DefaultVersionId' --output text)

echo "📌 Current policy version: $CURRENT_VERSION"
echo ""

# Create updated policy with all required permissions
echo "✏️  Creating comprehensive policy document..."

cat > /tmp/comprehensive_policy.json << 'EOF'
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
        "redshift:DescribeUsageLimits",
        "redshift:CreateClusterSnapshot",
        "redshift:ModifyCluster",
        "redshift:CreateTags",
        "redshift:DeleteTags"
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
        "redshift-serverless:RestoreFromSnapshot",
        "redshift-serverless:GetSnapshot",
        "redshift-serverless:ListSnapshots",
        "redshift-serverless:CreateSnapshot",
        "redshift-serverless:DeleteSnapshot",
        "redshift-serverless:TagResource",
        "redshift-serverless:UntagResource",
        "redshift-serverless:ListTagsForResource",
        "redshift-serverless:CreateSnapshotCopyConfiguration",
        "redshift-serverless:UpdateSnapshotCopyConfiguration",
        "redshift-serverless:DeleteSnapshotCopyConfiguration",
        "redshift-serverless:ListSnapshotCopyConfigurations",
        "redshift-serverless:CreateUsageLimit",
        "redshift-serverless:UpdateUsageLimit",
        "redshift-serverless:DeleteUsageLimit",
        "redshift-serverless:ListUsageLimits"
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
        "ec2:DescribeInternetGateways",
        "ec2:DescribeAvailabilityZones",
        "ec2:DescribeNetworkInterfaces",
        "ec2:CreateTags"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:ListRoles",
        "iam:GetRole",
        "iam:PassRole",
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PutRolePolicy",
        "iam:CreateServiceLinkedRole"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:DescribeKey",
        "kms:ListAliases",
        "kms:Decrypt",
        "kms:Encrypt",
        "kms:GenerateDataKey",
        "kms:CreateGrant"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret",
        "secretsmanager:CreateSecret",
        "secretsmanager:UpdateSecret"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "events:DescribeRule",
        "events:ListRules",
        "events:ListTargetsByRule",
        "events:PutRule",
        "events:PutTargets",
        "events:RemoveTargets",
        "events:DeleteRule"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "scheduler:GetSchedule",
        "scheduler:ListSchedules",
        "scheduler:ListScheduleGroups",
        "scheduler:CreateSchedule",
        "scheduler:UpdateSchedule",
        "scheduler:DeleteSchedule"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "redshift-data:ExecuteStatement",
        "redshift-data:DescribeStatement",
        "redshift-data:GetStatementResult",
        "redshift-data:ListStatements"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# List existing versions
echo "📋 Checking existing policy versions..."
VERSION_COUNT=$(aws iam list-policy-versions --policy-arn $POLICY_ARN --region $REGION --query 'length(Versions)' --output text)

if [ "$VERSION_COUNT" -ge 5 ]; then
    echo "⚠️  Policy has $VERSION_COUNT versions (max 5). Deleting oldest non-default version..."
    
    # Get oldest non-default version
    OLDEST_VERSION=$(aws iam list-policy-versions \
      --policy-arn $POLICY_ARN \
      --region $REGION \
      --query 'Versions[?IsDefaultVersion==`false`] | sort_by(@, &CreateDate) | [0].VersionId' \
      --output text)
    
    if [ -n "$OLDEST_VERSION" ] && [ "$OLDEST_VERSION" != "None" ]; then
        echo "🗑️  Deleting version: $OLDEST_VERSION"
        aws iam delete-policy-version \
          --policy-arn $POLICY_ARN \
          --version-id $OLDEST_VERSION \
          --region $REGION
        echo "✅ Old version deleted"
    fi
fi

# Create new policy version
echo ""
echo "🔄 Creating new policy version with comprehensive permissions..."
NEW_VERSION=$(aws iam create-policy-version \
  --policy-arn $POLICY_ARN \
  --policy-document file:///tmp/comprehensive_policy.json \
  --set-as-default \
  --region $REGION \
  --query 'PolicyVersion.VersionId' \
  --output text 2>&1)

if [ $? -eq 0 ]; then
    echo "✅ Successfully created new policy version: $NEW_VERSION"
    echo ""
    echo "📋 Added permissions for:"
    echo ""
    echo "   Redshift Serverless:"
    echo "   • Create/Update Namespace and Workgroup"
    echo "   • Restore from snapshot"
    echo "   • Manage snapshots"
    echo "   • Tag resources"
    echo ""
    echo "   EC2:"
    echo "   • Describe VPC, subnets, security groups"
    echo "   • Describe availability zones"
    echo "   • Create tags"
    echo ""
    echo "   IAM:"
    echo "   • Create and manage roles"
    echo "   • Pass roles to services"
    echo "   • Create service-linked roles"
    echo ""
    echo "   KMS:"
    echo "   • Encrypt/decrypt data"
    echo "   • Manage encryption keys"
    echo ""
    echo "   Secrets Manager:"
    echo "   • Manage database credentials"
    echo ""
    echo "🎉 All permissions updated successfully!"
    echo ""
    echo "✅ Your agent can now:"
    echo "   • Create Redshift Serverless workgroups"
    echo "   • Restore data from snapshots"
    echo "   • Manage encryption and credentials"
    echo "   • Configure networking"
else
    echo "❌ Failed to create new policy version"
    echo "$NEW_VERSION"
    exit 1
fi

# Clean up
rm -f /tmp/comprehensive_policy.json

echo ""
echo "🧪 Test the agent:"
echo "   ./chat"
echo ""
echo "   Then try: 'Create a workgroup from my cluster snapshot'"
