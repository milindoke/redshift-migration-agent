# Troubleshooting Lambda "Unhandled" Error

You got a `FunctionError: Unhandled` response, which means there's an exception in the Lambda function.

## Step 1: Refresh Your AWS Credentials

Your credentials are expired. Refresh them:

```bash
# Option 1: Configure with access keys
aws configure

# Option 2: If using SSO
aws sso login --profile YOUR_PROFILE

# Verify it works
aws sts get-caller-identity --region us-east-2
```

## Step 2: Check CloudWatch Logs

Once credentials are refreshed, check the logs:

```bash
# Run the log checker script
./check_lambda_logs.sh

# Or manually
aws logs tail /aws/lambda/redshift-migration-agent \
  --region us-east-2 \
  --since 10m \
  --follow
```

Look for error messages like:
- `ImportError` - Missing dependencies
- `ModuleNotFoundError` - Package not installed
- `ClientError` - AWS API errors
- `ValidationException` - Bedrock model access issues

## Common Issues and Fixes

### Issue 1: Bedrock Model Access Not Enabled

**Error:** `ValidationException: Could not resolve the foundation model`

**Fix:**
1. Go to: https://console.aws.amazon.com/bedrock
2. Click "Model access" → "Manage model access"
3. Enable "Claude 4.5 Sonnet"
4. Wait 2-3 minutes
5. Test again

### Issue 2: Missing Dependencies

**Error:** `ModuleNotFoundError: No module named 'strands'`

**Fix:** The Lambda deployment package might be missing dependencies.

Redeploy with all dependencies:

```bash
# Clean build
rm -rf .aws-sam

# Build with container (ensures all deps are included)
sam build --use-container

# Deploy
sam deploy
```

### Issue 3: Wrong Bedrock Model ID

**Error:** `ValidationException: Invocation of model ID ... isn't supported`

**Fix:** Update the model ID in the Lambda environment variables:

```bash
aws lambda update-function-configuration \
  --function-name redshift-migration-agent \
  --region us-east-2 \
  --environment Variables={BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0}
```

### Issue 4: Lambda Timeout

**Error:** Task timed out after 300.00 seconds

**Fix:** Increase timeout:

```bash
aws lambda update-function-configuration \
  --function-name redshift-migration-agent \
  --region us-east-2 \
  --timeout 600
```

### Issue 5: Out of Memory

**Error:** Runtime exited with error: signal: killed

**Fix:** Increase memory:

```bash
aws lambda update-function-configuration \
  --function-name redshift-migration-agent \
  --region us-east-2 \
  --memory-size 4096
```

### Issue 6: IAM Permissions

**Error:** `AccessDeniedException` or `UnauthorizedException`

**Fix:** Check the Lambda execution role has required permissions:

```bash
# Get the role name
aws lambda get-function \
  --function-name redshift-migration-agent \
  --region us-east-2 \
  --query 'Configuration.Role'

# Check attached policies
aws iam list-attached-role-policies \
  --role-name AgentExecutionRole
```

## Step 3: Test Locally (Optional)

Test the Lambda handler locally to see the exact error:

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements-agent.txt

# Run local test
python test_lambda_local.py
```

This will show you the exact error without needing to check CloudWatch logs.

## Step 4: Check Lambda Configuration

Verify the Lambda function is configured correctly:

```bash
# Get function configuration
aws lambda get-function-configuration \
  --function-name redshift-migration-agent \
  --region us-east-2

# Check environment variables
aws lambda get-function-configuration \
  --function-name redshift-migration-agent \
  --region us-east-2 \
  --query 'Environment.Variables'
```

Expected environment variables:
- `BEDROCK_MODEL_ID`: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`

## Step 5: Invoke with Better Error Handling

Try invoking with more details:

```bash
# Invoke and capture full response
aws lambda invoke \
  --function-name redshift-migration-agent \
  --region us-east-2 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"message":"Hello"}' \
  --log-type Tail \
  response.json

# Check response
cat response.json | jq .

# Check the logs (base64 encoded in response)
aws lambda invoke \
  --function-name redshift-migration-agent \
  --region us-east-2 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"message":"Hello"}' \
  --log-type Tail \
  response.json 2>&1 | grep LogResult | cut -d'"' -f4 | base64 -d
```

## Step 6: Redeploy if Needed

If the issue persists, redeploy:

```bash
# Clean everything
rm -rf .aws-sam

# Rebuild
sam build --use-container

# Deploy
sam deploy

# Test again
aws lambda invoke \
  --function-name redshift-migration-agent \
  --region us-east-2 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"message":"Hello"}' \
  response.json

cat response.json
```

## Quick Diagnosis Commands

Run these to quickly diagnose:

```bash
# 1. Check credentials
aws sts get-caller-identity --region us-east-2

# 2. Check function exists
aws lambda get-function --function-name redshift-migration-agent --region us-east-2

# 3. Check recent logs
aws logs tail /aws/lambda/redshift-migration-agent --region us-east-2 --since 5m

# 4. Check Bedrock access
aws bedrock list-foundation-models --region us-east-2 --query 'modelSummaries[?contains(modelId, `claude`)].modelId'

# 5. Test invoke
aws lambda invoke \
  --function-name redshift-migration-agent \
  --region us-east-2 \
  --payload '{"message":"test"}' \
  response.json && cat response.json
```

## Most Likely Causes

Based on the "Unhandled" error, the most likely causes are:

1. **Bedrock model access not enabled** (most common)
2. **Missing dependencies in Lambda package**
3. **Wrong Bedrock model ID**
4. **IAM permissions issue**

## Next Steps

1. ✅ Refresh AWS credentials: `aws configure`
2. ✅ Check CloudWatch logs: `./check_lambda_logs.sh`
3. ✅ Enable Bedrock access if needed
4. ✅ Redeploy if dependencies are missing: `sam build --use-container && sam deploy`
5. ✅ Test again

## Get Help

If you're still stuck, share:
- CloudWatch log output
- Lambda configuration: `aws lambda get-function-configuration --function-name redshift-migration-agent --region us-east-2`
- Error from `response.json`

---

**Start here:** Refresh credentials and run `./check_lambda_logs.sh`
