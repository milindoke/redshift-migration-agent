# Persistent Memory for Redshift Migration Agent

The Redshift Migration Agent uses AWS Bedrock AgentCore Memory to maintain conversation context across hours or even days. This allows the agent to remember:

- Previous conversations and decisions
- Migration progress and status
- User preferences and choices
- Cluster configurations discussed

## How It Works

The agent uses three types of memory strategies:

1. **Summary Memory** - Summarizes long conversations to maintain context
2. **User Preference Memory** - Learns and remembers your preferences
3. **Semantic Memory** - Extracts and stores important facts about your migrations

## Setup

### 1. Install Dependencies

The memory feature requires the `bedrock-agentcore` package, which is included in `requirements.txt`.

### 2. Create Memory Resource

Run the setup script once after deploying your Lambda:

```bash
python scripts/setup_memory.py --region us-east-2
```

This will create the memory resource and provide you with a `AGENTCORE_MEMORY_ID`.

### 3. Update Lambda Environment Variable

Set the memory ID as an environment variable:

```bash
aws lambda update-function-configuration \
  --function-name redshift-migration-agent \
  --environment Variables={AGENTCORE_MEMORY_ID=your-memory-id-here} \
  --region us-east-2
```

Or update it in the AWS Console:
- Go to Lambda → redshift-migration-agent → Configuration → Environment variables
- Add: `AGENTCORE_MEMORY_ID` = `your-memory-id`

## Usage

### With Session ID (Recommended)

Include a `session_id` in your requests to maintain conversation continuity:

```bash
aws lambda invoke \
  --function-name redshift-migration-agent \
  --payload '{
    "message": "List my Redshift clusters",
    "session_id": "migration-prod-cluster-2024"
  }' \
  response.json
```

### Session ID Best Practices

- Use descriptive session IDs: `migration-{cluster-name}-{date}`
- Reuse the same session_id for related conversations
- Different migrations = different session_ids
- Session IDs can be any string (alphanumeric, hyphens, underscores)

### With Actor ID (Optional)

Add an `actor_id` to personalize the experience per user:

```bash
aws lambda invoke \
  --function-name redshift-migration-agent \
  --payload '{
    "message": "What clusters did we discuss yesterday?",
    "session_id": "migration-prod-cluster-2024",
    "actor_id": "john.doe@example.com"
  }' \
  response.json
```

## Example Conversation Flow

### Day 1 - Initial Assessment

```bash
# First call - agent analyzes cluster
aws lambda invoke \
  --function-name redshift-migration-agent \
  --payload '{
    "message": "I want to migrate my prod-cluster to serverless",
    "session_id": "prod-migration-jan2024"
  }' \
  response.json
```

Agent response includes the session_id to use for follow-ups.

### Day 1 - Later

```bash
# Agent remembers the cluster and previous discussion
aws lambda invoke \
  --function-name redshift-migration-agent \
  --payload '{
    "message": "What were the WLM queues we found?",
    "session_id": "prod-migration-jan2024"
  }' \
  response.json
```

### Day 2 - Resume Migration

```bash
# Agent recalls entire conversation from Day 1
aws lambda invoke \
  --function-name redshift-migration-agent \
  --payload '{
    "message": "Let us proceed with the migration now",
    "session_id": "prod-migration-jan2024"
  }' \
  response.json
```

## Without Memory (Stateless Mode)

If you don't provide a `session_id`, the agent works in stateless mode:

```bash
aws lambda invoke \
  --function-name redshift-migration-agent \
  --payload '{
    "message": "List my Redshift clusters"
  }' \
  response.json
```

The agent will still work but won't remember previous conversations.

## Benefits for Long-Running Migrations

1. **Resume Anytime** - Start a migration, come back hours later, agent remembers everything
2. **Track Progress** - Agent remembers what steps were completed
3. **Context Preservation** - No need to re-explain cluster details
4. **Decision History** - Agent recalls your choices (single vs multiple workgroups, etc.)
5. **Multi-Day Migrations** - Perfect for migrations that span multiple days

## Memory Lifecycle

- **Sessions** are stored indefinitely until explicitly deleted
- **Summaries** are created automatically when conversations get long
- **Preferences** persist across all sessions for the same actor_id
- **Facts** are extracted and stored for quick retrieval

## Troubleshooting

### Memory Not Working

1. Check if `AGENTCORE_MEMORY_ID` is set:
   ```bash
   aws lambda get-function-configuration \
     --function-name redshift-migration-agent \
     --query 'Environment.Variables.AGENTCORE_MEMORY_ID'
   ```

2. Verify memory exists:
   ```bash
   aws bedrock list-memories --region us-east-2
   ```

3. Check Lambda logs for memory initialization errors:
   ```bash
   aws logs tail /aws/lambda/redshift-migration-agent --follow
   ```

### Creating Memory Manually

If the setup script fails, create memory manually:

```python
from bedrock_agentcore.memory import MemoryClient

client = MemoryClient(region_name='us-east-2')
memory = client.create_memory(
    name="RedshiftMigrationMemory",
    description="Persistent memory for Redshift migrations"
)
print(f"Memory ID: {memory['id']}")
```

## Cost Considerations

AgentCore Memory pricing:
- Storage: Minimal cost for conversation history
- API calls: Charged per memory operation
- Typical migration: $0.01 - $0.10 per session

For cost optimization:
- Use session_ids only for important migrations
- Clean up old sessions periodically
- Use stateless mode for simple queries

## Security

- Memory is stored in your AWS account
- IAM permissions control access
- Session IDs should not contain sensitive data
- Actor IDs can be email addresses or user IDs

## Advanced: Memory Management

### List All Sessions

```python
from bedrock_agentcore.memory import MemoryClient

client = MemoryClient(region_name='us-east-2')
sessions = client.list_memory_sessions(memory_id='your-memory-id')
print(sessions)
```

### Delete Old Sessions

```python
client.delete_memory_session(
    memory_id='your-memory-id',
    session_id='old-session-id'
)
```

### View Memory Contents

```python
session = client.get_memory_session(
    memory_id='your-memory-id',
    session_id='your-session-id'
)
print(session)
```
