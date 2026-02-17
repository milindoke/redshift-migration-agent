# Memory Setup Guide

The agent currently works WITHOUT memory (stateless mode). To enable persistent memory across conversations:

## Quick Setup (3 steps)

### 1. Install bedrock-agentcore locally

```bash
pip install bedrock-agentcore
```

### 2. Run the setup script

```bash
python scripts/setup_memory.py --region us-east-2
```

This will output a memory ID like: `mem-abc123def456`

### 3. Set the environment variable in Lambda

```bash
aws lambda update-function-configuration \
  --function-name redshift-migration-agent \
  --environment Variables={AGENTCORE_MEMORY_ID=mem-abc123def456} \
  --region us-east-2
```

Replace `mem-abc123def456` with your actual memory ID from step 2.

## Test Memory

```bash
# First conversation
aws lambda invoke \
  --function-name redshift-migration-agent \
  --payload '{"message":"My cluster name is prod-db-1","session_id":"test-session"}' \
  response.json

cat response.json

# Second conversation - agent should remember the cluster name
aws lambda invoke \
  --function-name redshift-migration-agent \
  --payload '{"message":"What was my cluster name?","session_id":"test-session"}' \
  response.json

cat response.json
```

## Without Memory

The agent works fine without memory setup. Just don't pass `session_id`:

```bash
aws lambda invoke \
  --function-name redshift-migration-agent \
  --payload '{"message":"List my clusters"}' \
  response.json
```

## Troubleshooting

### "bedrock-agentcore not found"

Install it:
```bash
pip install bedrock-agentcore
```

### "Permission denied" when creating memory

Make sure your AWS credentials have these permissions:
- `bedrock:CreateMemory`
- `bedrock:GetMemory`
- `bedrock:InvokeMemory`

### Memory not working after setup

1. Verify the environment variable is set:
   ```bash
   aws lambda get-function-configuration \
     --function-name redshift-migration-agent \
     --query 'Environment.Variables.AGENTCORE_MEMORY_ID'
   ```

2. Check Lambda logs:
   ```bash
   aws logs tail /aws/lambda/redshift-migration-agent --follow
   ```

3. Make sure you're passing `session_id` in your requests

## Cost

AgentCore Memory costs approximately $0.01-$0.10 per session depending on conversation length.
