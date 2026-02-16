# Update IAM Permissions

Guide to add missing EC2 permissions to the Lambda execution role.

## Quick Update

If you need to add the missing EC2 permissions to your deployed Lambda function:

```bash
# Refresh AWS credentials first
aws configure

# Run the update script
scripts/utils/update_ec2_permissions.sh
```

## What Gets Added

The script adds these EC2 permissions:

```json
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
}
```

## Why These Permissions?

These permissions allow the agent to:
- **DescribeAccountAttributes**: Check account-level EC2 settings
- **DescribeVpcs**: List and inspect VPCs for cluster migration
- **DescribeSubnets**: Get subnet details for network configuration
- **DescribeSecurityGroups**: Retrieve security group information
- **DescribeAddresses**: Check Elastic IP addresses
- **DescribeInternetGateways**: Verify internet gateway configuration

## Manual Update (Alternative)

If you prefer to update manually:

### Option 1: AWS Console

1. Go to [IAM Console](https://console.aws.amazon.com/iam)
2. Click "Policies" → Search for "RedshiftAgentExecutionPolicy"
3. Click the policy → "Edit policy"
4. Add the EC2 permissions from above
5. Click "Review policy" → "Save changes"

### Option 2: AWS CLI

```bash
# Get your account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create policy document
cat > ec2-permissions.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
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
    }
  ]
}
EOF

# Create new policy version
aws iam create-policy-version \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/RedshiftAgentExecutionPolicy \
  --policy-document file://ec2-permissions.json \
  --set-as-default
```

### Option 3: Redeploy with Updated Template

The template.yaml has been updated with the new permissions. Redeploy:

```bash
# Refresh credentials
aws configure

# Redeploy
./deploy
```

## Verify Permissions

After updating, verify the permissions:

```bash
# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Get policy document
aws iam get-policy-version \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/RedshiftAgentExecutionPolicy \
  --version-id $(aws iam get-policy \
    --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/RedshiftAgentExecutionPolicy \
    --query 'Policy.DefaultVersionId' \
    --output text) \
  --query 'PolicyVersion.Document' \
  --output json
```

Look for the EC2 permissions in the output.

## Test the Agent

After updating permissions, test the agent:

```bash
./chat
```

Then try:
```
You: List my Redshift clusters
Agent: [Should now work without permission errors]
```

## Troubleshooting

### "ExpiredToken" Error

Your AWS credentials are expired. Refresh them:

```bash
aws configure
# Or if using SSO:
aws sso login
```

### "AccessDenied" Error

You need IAM permissions to update policies. Required permissions:
- `iam:CreatePolicyVersion`
- `iam:GetPolicy`
- `iam:GetPolicyVersion`

### "Policy Version Limit Exceeded"

IAM policies can have max 5 versions. Delete old versions:

```bash
# List versions
aws iam list-policy-versions \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/RedshiftAgentExecutionPolicy

# Delete old version (not the default)
aws iam delete-policy-version \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/RedshiftAgentExecutionPolicy \
  --version-id v1
```

## What's Updated

The update script modifies:
- **Policy**: `RedshiftAgentExecutionPolicy`
- **Attached to**: `AgentExecutionRole` (Lambda execution role)
- **Effect**: Lambda function can now describe EC2 resources

## No Downtime

Updating IAM permissions has no downtime. The Lambda function continues to run, and new permissions are available immediately.

## Rollback

If you need to rollback:

```bash
# List policy versions
aws iam list-policy-versions \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/RedshiftAgentExecutionPolicy

# Set previous version as default
aws iam set-default-policy-version \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/RedshiftAgentExecutionPolicy \
  --version-id v1  # Replace with previous version
```

## Questions?

- Check [Troubleshooting Guide](TROUBLESHOOT_LAMBDA.md)
- Check CloudWatch logs: `scripts/utils/check_lambda_logs.sh`
- Open an issue on GitHub

---

**Quick update:** `scripts/utils/update_ec2_permissions.sh`
