# Deploy Your Agent to AWS - Quick Guide

## Prerequisites Check

### 1. Install SAM CLI (Required)

You need SAM CLI to deploy. Install it:

```bash
# macOS (using Homebrew)
brew install aws-sam-cli

# Verify installation
sam --version
```

### 2. Refresh AWS Credentials

Your AWS credentials are expired. Refresh them:

```bash
# Configure AWS credentials
aws configure

# Or if using SSO
aws sso login --profile YOUR_PROFILE

# Verify credentials work
aws sts get-caller-identity
```

You should see your account ID and user info.

### 3. Enable Bedrock Model Access

Before deploying, enable Claude Sonnet 4.5 in Bedrock:

1. Go to: https://console.aws.amazon.com/bedrock
2. Click "Model access" in left menu
3. Click "Manage model access"
4. Find "Claude 4.5 Sonnet" and enable it
5. Click "Save changes"
6. Wait 2-3 minutes for access to be granted

## Deployment Options

### Option 1: Quick Deploy Script (Easiest)

```bash
# Make sure you're in the project directory
cd ~/Kiro\ projects/migrateRedshiftProvisionedToServerless

# Run the quick deploy script
./quick_deploy.sh
```

This script will:
- Check prerequisites
- Build the application
- Deploy to AWS with guided prompts
- Show you next steps

### Option 2: Manual SAM Deploy

```bash
# Build the application
sam build

# Deploy with guided setup
sam deploy --guided
```

When prompted, answer:
- **Stack Name**: `redshift-migration-agent` (or your choice)
- **AWS Region**: `us-east-2` (or your preferred region)
- **Parameter BedrockModelId**: Press Enter (uses default)
- **Parameter FunctionMemorySize**: Press Enter (uses 2048 MB)
- **Parameter FunctionTimeout**: Press Enter (uses 300 seconds)
- **Confirm changes before deploy**: `Y`
- **Allow SAM CLI IAM role creation**: `Y`
- **Disable rollback**: `N`
- **Save arguments to configuration file**: `Y`
- **SAM configuration file**: Press Enter (uses samconfig.toml)
- **SAM configuration environment**: Press Enter (uses default)

### Option 3: Deploy to Specific Region

```bash
sam build
sam deploy --guided --region us-west-2
```

## What Gets Deployed

The deployment creates:

1. **Lambda Function**: `redshift-migration-agent`
   - Runtime: Python 3.11
   - Memory: 2048 MB
   - Timeout: 300 seconds

2. **IAM Role**: `AgentExecutionRole`
   - Permissions for Redshift, Bedrock, EC2, IAM, EventBridge

3. **IAM Policy**: `RedshiftAgentExecutionPolicy`
   - Managed policy with all required permissions

## After Deployment

### 1. Verify Deployment

```bash
# Check Lambda function exists
aws lambda get-function --function-name redshift-migration-agent

# Get function ARN
aws lambda get-function \
  --function-name redshift-migration-agent \
  --query 'Configuration.FunctionArn' \
  --output text
```

### 2. Test the Agent

```bash
# Test with a simple query
aws lambda invoke \
  --function-name redshift-migration-agent \
  --cli-binary-format raw-in-base64-out \
  --payload '{"message":"Hello, can you help me migrate my Redshift cluster?"}' \
  response.json

# View the response
cat response.json
```

### 3. List Your Redshift Clusters

```bash
aws lambda invoke \
  --function-name redshift-migration-agent \
  --cli-binary-format raw-in-base64-out \
  --payload '{"message":"List my Redshift clusters in us-east-2"}' \
  response.json

cat response.json
```

## Deployment Cost

Estimated monthly cost:
- **Lambda**: $0-20 (first 1M requests free)
- **Bedrock**: $3-10 (based on usage)
- **Total**: ~$5-30/month

## Troubleshooting

### SAM Build Fails

```bash
# Clean and rebuild
rm -rf .aws-sam
sam build --use-container
```

### Deployment Fails - Insufficient Permissions

Make sure your IAM user has these permissions:
- `cloudformation:*`
- `lambda:*`
- `iam:CreateRole`
- `iam:AttachRolePolicy`
- `s3:CreateBucket`
- `s3:PutObject`

### Bedrock Access Denied

1. Check model access in Bedrock Console
2. Verify your region supports Claude Sonnet 4.5
3. Wait a few minutes after enabling access

### Lambda Timeout During Test

This is normal for first invocation (cold start). Try again:

```bash
aws lambda invoke \
  --function-name redshift-migration-agent \
  --cli-binary-format raw-in-base64-out \
  --payload '{"message":"Hello"}' \
  response.json
```

## View Deployment Details

```bash
# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name redshift-migration-agent \
  --query 'Stacks[0].Outputs'

# View Lambda function
aws lambda get-function --function-name redshift-migration-agent

# View logs
aws logs tail /aws/lambda/redshift-migration-agent --follow
```

## Update the Agent

If you make changes and want to redeploy:

```bash
sam build
sam deploy
```

## Delete the Agent

To remove everything:

```bash
aws cloudformation delete-stack --stack-name redshift-migration-agent

# Wait for deletion to complete
aws cloudformation wait stack-delete-complete --stack-name redshift-migration-agent
```

## Next Steps After Deployment

1. ✅ Test the agent with sample queries
2. ✅ Add team members to the user group
3. ✅ Set up CloudWatch alarms for monitoring
4. ✅ Create a migration plan for your clusters
5. ✅ Run a test migration on a non-production cluster

## Need Help?

- Full deployment guide: `DEPLOY.md`
- Troubleshooting: Check CloudWatch logs
- Issues: https://github.com/milindoke/redshift-migration-agent/issues

---

**Ready to deploy?**

1. Install SAM CLI: `brew install aws-sam-cli`
2. Refresh AWS credentials: `aws configure`
3. Enable Bedrock access
4. Run: `./quick_deploy.sh`

Good luck! 🚀
