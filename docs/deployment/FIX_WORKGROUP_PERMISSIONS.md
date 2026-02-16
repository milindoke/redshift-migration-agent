# Fix Workgroup Creation Permissions

Complete guide to fix IAM permissions for creating workgroups and restoring from snapshots.

## Quick Fix

If you're getting permission errors when creating workgroups:

```bash
# Refresh AWS credentials
aws configure

# Run the comprehensive permissions update
scripts/utils/update_all_permissions.sh
```

This adds all required permissions for:
- ✅ Creating Redshift Serverless namespaces and workgroups
- ✅ Restoring data from snapshots
- ✅ Managing encryption (KMS)
- ✅ Managing credentials (Secrets Manager)
- ✅ Configuring networking (VPC, subnets, security groups)
- ✅ Creating and passing IAM roles

## What Permissions Are Added?

### Redshift Serverless (Extended)
```json
{
  "Effect": "Allow",
  "Action": [
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
    "redshift-serverless:ListTagsForResource"
  ],
  "Resource": "*"
}
```

### EC2 (Extended)
```json
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
}
```

### IAM (Extended)
```json
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
}
```

### KMS (New)
```json
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
}
```

### Secrets Manager (New)
```json
{
  "Effect": "Allow",
  "Action": [
    "secretsmanager:GetSecretValue",
    "secretsmanager:DescribeSecret",
    "secretsmanager:CreateSecret",
    "secretsmanager:UpdateSecret"
  ],
  "Resource": "*"
}
```

### Redshift (Extended)
```json
{
  "Effect": "Allow",
  "Action": [
    "redshift:CreateTags",
    "redshift:DeleteTags"
  ],
  "Resource": "*"
}
```

## Why These Permissions?

### For Workgroup Creation
- **CreateNamespace/CreateWorkgroup**: Create the serverless resources
- **UpdateNamespace/UpdateWorkgroup**: Configure settings
- **TagResource**: Apply tags from source cluster
- **DescribeVpcs/Subnets/SecurityGroups**: Configure networking
- **CreateServiceLinkedRole**: Create required service roles

### For Snapshot Restoration
- **RestoreFromSnapshot**: Restore data from provisioned cluster
- **GetSnapshot/ListSnapshots**: Access snapshot information
- **kms:Decrypt/Encrypt**: Handle encrypted snapshots
- **secretsmanager:GetSecretValue**: Retrieve database credentials

### For IAM Role Management
- **CreateRole**: Create namespace default role if needed
- **AttachRolePolicy**: Attach policies to roles
- **PassRole**: Allow Redshift to assume roles
- **PutRolePolicy**: Add inline policies

## Common Permission Errors

### Error: "User is not authorized to perform: redshift-serverless:CreateWorkgroup"

**Fix:** Run the update script
```bash
scripts/utils/update_all_permissions.sh
```

### Error: "User is not authorized to perform: iam:PassRole"

**Cause:** Missing IAM PassRole permission

**Fix:** The update script adds this. If you updated manually, ensure PassRole is included.

### Error: "User is not authorized to perform: kms:Decrypt"

**Cause:** Snapshot is encrypted, but Lambda can't decrypt

**Fix:** The update script adds KMS permissions.

### Error: "Access Denied when calling CreateServiceLinkedRole"

**Cause:** Missing CreateServiceLinkedRole permission

**Fix:** The update script adds this for creating required service roles.

## Manual Update (Alternative)

If you prefer to update manually via AWS Console:

1. Go to [IAM Console](https://console.aws.amazon.com/iam)
2. Click "Policies" → Search for "RedshiftAgentExecutionPolicy"
3. Click the policy → "Edit policy"
4. Switch to JSON tab
5. Add the permissions from above
6. Click "Review policy" → "Save changes"

## Verify Permissions

After updating, verify:

```bash
# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# View policy
aws iam get-policy-version \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/RedshiftAgentExecutionPolicy \
  --version-id $(aws iam get-policy \
    --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/RedshiftAgentExecutionPolicy \
    --query 'Policy.DefaultVersionId' \
    --output text) \
  --query 'PolicyVersion.Document' \
  --output json | jq .
```

Look for the new permissions in the output.

## Test the Agent

After updating permissions:

```bash
./chat
```

Try these commands:
```
You: Create a namespace called test-namespace
Agent: [Should succeed]

You: Create a workgroup from my cluster snapshot
Agent: [Should succeed]

You: Restore data from snapshot snap-123 to workgroup my-wg
Agent: [Should succeed]
```

## Troubleshooting

### "Policy Version Limit Exceeded"

IAM policies can have max 5 versions. The update script automatically deletes old versions.

If you need to manually delete:

```bash
# List versions
aws iam list-policy-versions \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/RedshiftAgentExecutionPolicy

# Delete old version (not the default)
aws iam delete-policy-version \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/RedshiftAgentExecutionPolicy \
  --version-id v1
```

### "ExpiredToken" Error

Refresh your AWS credentials:

```bash
aws configure
# Or if using SSO:
aws sso login
```

### Still Getting Permission Errors?

Check CloudWatch logs for the specific permission denied:

```bash
scripts/utils/check_lambda_logs.sh
```

Look for lines like:
```
User: arn:aws:sts::123456789012:assumed-role/AgentExecutionRole/redshift-migration-agent 
is not authorized to perform: redshift-serverless:CreateWorkgroup
```

Then add that specific permission.

## Security Considerations

### Least Privilege

These permissions are scoped to what's needed for migration. After migration is complete, you can:

1. Remove unused permissions
2. Restrict to specific resources (instead of `"Resource": "*"`)
3. Add condition statements for additional security

### Resource-Specific Permissions (Optional)

To restrict to specific resources:

```json
{
  "Effect": "Allow",
  "Action": [
    "redshift-serverless:CreateWorkgroup",
    "redshift-serverless:UpdateWorkgroup"
  ],
  "Resource": "arn:aws:redshift-serverless:us-east-2:123456789012:workgroup/*"
}
```

### Audit Trail

All actions are logged in CloudTrail. Review:

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=AgentExecutionRole \
  --max-results 50
```

## What's Updated

The update modifies:
- **Policy**: `RedshiftAgentExecutionPolicy`
- **Attached to**: `AgentExecutionRole` (Lambda execution role)
- **Effect**: Lambda can now create workgroups and restore snapshots

## No Downtime

Updating IAM permissions has no downtime. Changes are effective immediately.

## Rollback

If needed, rollback to previous version:

```bash
# List versions
aws iam list-policy-versions \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/RedshiftAgentExecutionPolicy

# Set previous version as default
aws iam set-default-policy-version \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/RedshiftAgentExecutionPolicy \
  --version-id v2  # Replace with previous version
```

## Next Steps

After fixing permissions:

1. ✅ Test workgroup creation: `./chat` → "Create a workgroup"
2. ✅ Test snapshot restoration: "Restore from snapshot"
3. ✅ Run a complete migration: "Migrate cluster xyz to serverless"

## Questions?

- Check [Troubleshooting Guide](TROUBLESHOOT_LAMBDA.md)
- Check CloudWatch logs: `scripts/utils/check_lambda_logs.sh`
- Open an issue on GitHub

---

**Quick fix:** `scripts/utils/update_all_permissions.sh`

**Your agent can now create workgroups and restore data!** 🎉
