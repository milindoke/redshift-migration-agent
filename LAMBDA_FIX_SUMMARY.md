# Lambda Error Fixed - Summary

## The Problem

Your Lambda function was failing with:
```
Runtime.ImportModuleError: Unable to import module 'lambda_handler': 
No module named 'pydantic_core._pydantic_core'
```

## Root Cause

The `pydantic_core` package (a dependency of `strands-agents`) contains compiled C extensions that need to be built specifically for the Lambda runtime environment (Amazon Linux 2). When you built the package on macOS, it compiled for macOS, not for Lambda.

## The Fix

I've made two changes:

### 1. Created `requirements.txt`
SAM CLI looks for `requirements.txt` (not `requirements-agent.txt`) to install dependencies.

### 2. Updated `template.yaml`
Added build metadata to ensure proper compilation:
```yaml
Metadata:
  BuildMethod: python3.11
  BuildArchitecture: x86_64
```

### 3. Use Container Build
The `--use-container` flag tells SAM to build inside a Docker container that matches the Lambda runtime environment, ensuring all packages are compiled correctly.

## How to Fix

Run the redeploy script:

```bash
./redeploy.sh
```

This will:
1. Clean previous build artifacts
2. Build using a container (ensures proper compilation)
3. Deploy to AWS
4. Test the function

**Note:** The container build takes longer (3-5 minutes) but ensures everything works correctly.

## Manual Steps (if you prefer)

```bash
# Clean
rm -rf .aws-sam

# Build with container
sam build --use-container

# Deploy
sam deploy

# Test
aws lambda invoke \
  --function-name redshift-migration-agent \
  --region us-east-2 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"message":"Hello"}' \
  response.json

cat response.json
```

## Why This Happened

When you first deployed, SAM built the package on your macOS machine. Packages with C extensions (like `pydantic_core`) get compiled for the host OS. Lambda runs on Amazon Linux 2, so those compiled extensions don't work.

The `--use-container` flag solves this by building inside a Docker container that matches Lambda's environment.

## Verification

After redeploying, you should see:
- ✅ No import errors in CloudWatch logs
- ✅ Function returns a proper response
- ✅ Agent responds to your messages

## Future Deployments

Always use container builds for Lambda:
```bash
sam build --use-container
sam deploy
```

Or use the quick script:
```bash
./redeploy.sh
```

## What Changed

Files modified:
- ✅ `template.yaml` - Added build metadata
- ✅ `requirements.txt` - Created (copy of requirements-agent.txt)
- ✅ `redeploy.sh` - Quick redeploy script

## Next Steps

1. Run `./redeploy.sh`
2. Wait for deployment (3-5 minutes)
3. Test the agent
4. Start using it!

## Common Questions

**Q: Why does it take longer now?**
A: Container builds are slower but ensure compatibility. It's a one-time cost per deployment.

**Q: Do I need Docker installed?**
A: Yes, SAM uses Docker for container builds. Install Docker Desktop if you don't have it.

**Q: Can I avoid container builds?**
A: Not recommended for packages with C extensions. You'd need to build on Amazon Linux 2.

**Q: Will this happen again?**
A: No, as long as you use `sam build --use-container` for future deployments.

## Troubleshooting

If the redeploy fails:

**Docker not running:**
```bash
# Start Docker Desktop, then retry
./redeploy.sh
```

**SAM not installed:**
```bash
brew install aws-sam-cli
```

**Build fails:**
```bash
# Try with verbose output
sam build --use-container --debug
```

**Still getting import errors:**
```bash
# Check logs
aws logs tail /aws/lambda/redshift-migration-agent --region us-east-2 --since 5m
```

## Success Indicators

After successful redeploy, you'll see:
- Build completes without errors
- Deploy shows "Successfully created/updated stack"
- Test invocation returns agent response
- CloudWatch logs show "Agent initialized successfully"

---

**Ready to fix?** Run: `./redeploy.sh`
