# Memory Setup Guide

## Memory is Enabled by Default! 🎉

The agent now automatically creates and uses persistent memory. No manual setup required!

## How It Works

1. **First invocation**: Agent automatically creates a memory resource
2. **Subsequent invocations**: Agent reuses the existing memory
3. **Sessions**: Use `session_id` to group related conversations

## Usage

### Auto-generated session (each call is separate)
```bash
aws lambda invoke \
  --function-name redshift-migration-agent \
  --payload '{"message":"List my clusters"}' \
  response.json
```

### Named session (conversations persist)
```bash
# First conversation
aws lambda invoke \
  --function-name redshift-migration-agent \
  --payload '{"message":"My cluster name is prod-db-1","session_id":"my-migration"}' \
  response.json

# Hours later - agent remembers!
aws lambda invoke \
  --function-name redshift-migration-agent \
  --payload '{"message":"What was my cluster name?","session_id":"my-migration"}' \
  response.json
```

## Session ID Best Practices

- Use descriptive names: `migration-prod-cluster-2024`
- Reuse the same session_id for related work
- Different migrations = different session_ids
- If not provided, auto-generated (but won't persist across calls)

## Optional: Set AGENTCORE_MEMORY_ID

To skip the automatic memory creation on first run, you can pre-create and set the memory ID:

```bash
# 1. Create memory
python scripts/setup_memory.py --region us-east-2

# 2. Set environment variable (use the ID from step 1)
aws lambda update-function-configuration \
  --function-name redshift-migration-agent \
  --environment Variables={AGENTCORE_MEMORY_ID=mem-abc123def456} \
  --region us-east-2
```

This is optional - the agent will create memory automatically if not set.

## Troubleshooting

### Memory not persisting

Make sure you're using the same `session_id` across calls:
```bash
# ❌ Different sessions (won't remember)
aws lambda invoke --payload '{"message":"Hello","session_id":"session-1"}' response.json
aws lambda invoke --payload '{"message":"What did I say?","session_id":"session-2"}' response.json

# ✅ Same session (will remember)
aws lambda invoke --payload '{"message":"Hello","session_id":"my-session"}' response.json
aws lambda invoke --payload '{"message":"What did I say?","session_id":"my-session"}' response.json
```

### Check Lambda logs
```bash
aws logs tail /aws/lambda/redshift-migration-agent --follow
```

Look for messages like:
- `✅ Memory created: mem-xxx` (first run)
- `✅ Found existing memory: mem-xxx` (subsequent runs)
- `✅ Memory enabled: session_id=xxx`

## Cost

AgentCore Memory costs approximately $0.01-$0.10 per session depending on conversation length.
The agent automatically manages memory resources efficiently.
