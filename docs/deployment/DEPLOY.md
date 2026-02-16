# Deployment Guide

Complete guide to deploy the Redshift Migration Agent to your AWS account.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **SAM CLI** installed
4. **Python 3.11+** installed
5. **Bedrock Model Access** enabled for Claude Sonnet 4.5

### Install AWS CLI

```bash
# macOS
brew install awscli

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Windows
# Download from: https://awscli.amazonaws.com/AWSCLIV2.msi
```

### Install SAM CLI

```bash
# macOS
brew install aws-sam-cli

# Linux
wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
unzip aws-sam-cli-linux-x86_64.zip -d sam-installation
sudo ./sam-installation/install

# Windows
# Download from: https://github.com/aws/aws-sam-cli/releases/latest/download/AWS_SAM_CLI_64_PY3.msi
```

### Configure AWS Credentials

```bash
aws configure
# Enter your:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region (e.g., us-east-2)
# - Default output format (json)
```

### Enable Bedrock Model Access

1. Go to [Bedrock Console](https://console.aws.amazon.com/bedrock)
2. Click "Model access" in the left menu
3. Click "Manage model access"
4. Enable "Claude 4.5 Sonnet"
5. Click "Save changes"
6. Wait 2-3 minutes for access to be granted

## Deployment Methods

### Method 1: Quick Deploy (Recommended)

```bash
# Clone the repository
git clone https://github.com/milindoke/redshift-migration-agent.git
cd redshift-migration-agent

# Run quick deploy
./quick_deploy.sh
```

This script will:
- Check prerequisites
- Build the application
- Deploy to AWS
- Show next steps

### Method 2: Manual SAM Deploy

```bash
# Clone the repository
git clone https://github.com/milindoke/redshift-migration-agent.git
cd redshift-migration-agent

# Build
sam build

# Deploy with guided prompts
sam deploy --guided
```

Answer the prompts:
- Stack Name: `redshift-migration-agent` (or your choice)
- AWS Region: `us-east-2` (or your choice)
- Parameter BedrockModelId: Press Enter for default
- Parameter FunctionMemorySize: Press Enter for default (2048)
- Parameter FunctionTimeout: Press Enter for default (300)
- Confirm changes before deploy: `Y`
- Allow SAM CLI IAM role creation: `Y`
- Disable rollback: `N`
- Save arguments to configuration file: `Y`
- SAM configuration file: Press Enter for default
- SAM configuration environment: Press Enter for default

### Method 3: CloudFormation Console

1. Build and package:
```bash
sam build
sam package \
  --template-file template.yaml \
  --output-template-file packaged.yaml \
  --s3-bucket YOUR-DEPLOYMENT-BUCKET
```

2. Go to [CloudFormation Console](https://console.aws.amazon.com/cloudformation)
3. Click "Create stack" → "With new resources"
4. Upload `packaged.yaml`
5. Follow the wizard

## Post-Deployment Setup

### 1. Add Users to Authorized Group

```bash
# Add yourself
aws iam add-user-to-group \
  --user-name YOUR_USERNAME \
  --group-name RedshiftMigrationAgentUsers

# Add other users
aws iam add-user-to-group \
  --user-name ANOTHER_USER \
  --group-name RedshiftMigrationAgentUsers
```

### 2. Test the Agent

```bash
# Invoke via Lambda
aws lambda invoke \
  --function-name redshift-migration-agent \
  --cli-binary-format raw-in-base64-out \
  --payload '{"message":"List my Redshift clusters in us-east-2"}' \
  response.json

# View response
cat response.json
```

### 3. Get Stack Outputs

```bash
aws cloudformation describe-stacks \
  --stack-name redshift-migration-agent \
  --query 'Stacks[0].Outputs'
```

This shows:
- Lambda Function ARN
- API Gateway endpoint
- IAM Group name
- IAM Policy ARN

## Configuration Options

### Custom Bedrock Model

```bash
sam deploy \
  --parameter-overrides BedrockModelId=us.anthropic.claude-sonnet-4-5-20250929-v1:0
```

### Increase Memory/Timeout

```bash
sam deploy \
  --parameter-overrides FunctionMemorySize=4096 FunctionTimeout=600
```

### Different Region

```bash
sam deploy --region us-west-2
```

## Verification

### Check Lambda Function

```bash
aws lambda get-function --function-name redshift-migration-agent
```

### Check IAM Resources

```bash
# List group members
aws iam get-group --group-name RedshiftMigrationAgentUsers

# Check policy
aws iam get-policy --policy-arn $(aws cloudformation describe-stacks \
  --stack-name redshift-migration-agent \
  --query 'Stacks[0].Outputs[?OutputKey==`InvokePolicyArn`].OutputValue' \
  --output text)
```

### View Logs

```bash
# Get latest log stream
aws logs tail /aws/lambda/redshift-migration-agent --follow
```

## Troubleshooting

### Build Fails

```bash
# Clean and rebuild
rm -rf .aws-sam
sam build --use-container
```

### Deployment Fails - Insufficient Permissions

Ensure your IAM user has these permissions:
- `cloudformation:*`
- `lambda:*`
- `iam:CreateRole`
- `iam:AttachRolePolicy`
- `s3:CreateBucket`
- `s3:PutObject`

### Bedrock Access Denied

1. Check model access in Bedrock Console
2. Verify region supports Claude Sonnet 4.5
3. Wait a few minutes after enabling access

### Lambda Timeout

Increase timeout:
```bash
aws lambda update-function-configuration \
  --function-name redshift-migration-agent \
  --timeout 600
```

### Out of Memory

Increase memory:
```bash
aws lambda update-function-configuration \
  --function-name redshift-migration-agent \
  --memory-size 4096
```

## Updating the Agent

### Update Code

```bash
# Pull latest changes
git pull origin main

# Rebuild and deploy
sam build
sam deploy
```

### Update Configuration Only

```bash
aws lambda update-function-configuration \
  --function-name redshift-migration-agent \
  --environment Variables={BEDROCK_MODEL_ID=new-model-id}
```

## Uninstalling

```bash
# Delete the stack
aws cloudformation delete-stack --stack-name redshift-migration-agent

# Wait for deletion
aws cloudformation wait stack-delete-complete --stack-name redshift-migration-agent

# Clean up S3 bucket (if created)
aws s3 rb s3://aws-sam-cli-managed-default-samclisourcebucket-* --force
```

## Cost Optimization

### Reduce Memory

If migrations are small:
```bash
sam deploy --parameter-overrides FunctionMemorySize=1024
```

### Use Reserved Capacity

For frequent use, consider Lambda Reserved Concurrency to reduce costs.

### Monitor Usage

```bash
# Check invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=redshift-migration-agent \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum
```

## Security Best Practices

1. **Least Privilege**: Only add necessary users to the group
2. **Audit Logs**: Enable CloudTrail for Lambda invocations
3. **Encryption**: Lambda environment variables are encrypted by default
4. **VPC**: Deploy Lambda in VPC if accessing private Redshift clusters
5. **Secrets**: Use AWS Secrets Manager for sensitive data

## Multi-Region Deployment

Deploy to multiple regions:

```bash
# Deploy to us-east-1
sam deploy --region us-east-1 --stack-name redshift-agent-us-east-1

# Deploy to us-west-2
sam deploy --region us-west-2 --stack-name redshift-agent-us-west-2

# Deploy to eu-west-1
sam deploy --region eu-west-1 --stack-name redshift-agent-eu-west-1
```

## Production Checklist

- [ ] Bedrock model access enabled
- [ ] Lambda deployed successfully
- [ ] IAM group created
- [ ] Users added to group
- [ ] Test invocation successful
- [ ] CloudWatch logs working
- [ ] Cost alerts configured
- [ ] Documentation shared with team
- [ ] Backup/disaster recovery plan
- [ ] Monitoring dashboard created

## Support

- GitHub Issues: https://github.com/milindoke/redshift-migration-agent/issues
- Documentation: https://github.com/milindoke/redshift-migration-agent
- AWS Support: https://console.aws.amazon.com/support

---

**Ready to deploy?** Run `./quick_deploy.sh` to get started!
