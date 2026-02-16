# Chat with Your Redshift Migration Agent

Natural conversation interface for your Lambda-based agent.

## Quick Start

### Option 1: Simple Chat (Recommended)

```bash
python3 chat_with_agent.py
```

Features:
- ✅ Natural conversation flow
- ✅ Colored output
- ✅ Simple and fast
- ✅ No dependencies

### Option 2: Advanced Chat (Best Experience)

```bash
# Install rich for better formatting (optional)
pip install rich

# Start chat
python3 chat_advanced.py
```

Features:
- ✅ Beautiful markdown formatting
- ✅ Conversation history
- ✅ Auto-save conversations
- ✅ Progress indicators
- ✅ Command history

## Example Conversation

```
You: Hello! Can you help me migrate my Redshift cluster?

Agent: Hello! I'd be happy to help you migrate your Redshift provisioned 
cluster to Redshift Serverless! 🚀

Let me ask you a few questions...

You: List my clusters in us-east-2

Agent: I'll list all your Redshift clusters in us-east-2...
[Lists clusters]

You: Extract config from my-cluster-1

Agent: I'll extract the configuration from my-cluster-1...
[Shows extracted config]

You: Migrate it to serverless

Agent: I'll start the migration process...
[Performs migration]
```

## Available Commands

While chatting, you can use these commands:

- `exit` or `quit` - End the conversation
- `clear` - Clear the screen
- `history` - Show conversation history (advanced chat only)
- `save` - Save conversation to file (advanced chat only)
- `help` - Get migration guidance

## What You Can Ask

### Getting Started
- "List my Redshift clusters"
- "What can you help me with?"
- "How do I migrate a cluster?"

### Cluster Information
- "Show me details about cluster xyz"
- "Extract configuration from my-cluster"
- "What parameters does my cluster use?"

### Migration
- "Migrate cluster abc to serverless"
- "Create a snapshot of my cluster"
- "Apply configuration to serverless workgroup"
- "Migrate scheduled queries"

### Troubleshooting
- "Why did the migration fail?"
- "How do I fix parameter mapping issues?"
- "What's the status of my migration?"

## Tips for Best Experience

1. **Be Natural**: Ask questions like you would to a colleague
   - ✅ "Can you list my clusters?"
   - ✅ "Show me what's in us-east-2"
   - ✅ "Help me migrate cluster-1"

2. **Provide Context**: The agent remembers your conversation
   - "List clusters" → "Extract config from the first one" → "Migrate it"

3. **Ask for Help**: If unsure, just ask
   - "What should I do next?"
   - "What are my options?"
   - "Can you explain this?"

4. **Use Commands**: Speed up common tasks
   - Type `help` for quick guidance
   - Type `history` to review what you've done
   - Type `save` to keep a record

## Conversation History

Advanced chat automatically saves conversations to:
```
~/.redshift-agent/conversations/conversation_YYYYMMDD_HHMMSS.json
```

You can review past conversations anytime!

## Troubleshooting

### "Error connecting to Lambda"

Make sure:
1. AWS credentials are configured: `aws configure`
2. You have permission to invoke the function
3. The function exists in us-east-2

### "No response received"

Check:
1. Lambda function is deployed: `aws lambda get-function --function-name redshift-migration-agent --region us-east-2`
2. CloudWatch logs for errors: `aws logs tail /aws/lambda/redshift-migration-agent --region us-east-2`

### "Module 'rich' not found"

Either:
- Install rich: `pip install rich`
- Use simple chat: `python3 chat_with_agent.py`

## Keyboard Shortcuts

- `Ctrl+C` - Interrupt current operation
- `Ctrl+D` - Exit (Unix/Mac)
- `↑` / `↓` - Command history (in some terminals)

## Examples

### Quick Migration

```bash
$ python3 chat_with_agent.py

You: List my clusters in us-east-2
Agent: [Shows clusters]

You: Migrate prod-cluster-1 to serverless with snapshot
Agent: [Performs migration]

You: exit
```

### Step-by-Step Migration

```bash
$ python3 chat_advanced.py

You: I want to migrate my cluster but I'm not sure how
Agent: [Explains options]

You: Extract config from prod-db first
Agent: [Extracts and shows config]

You: Looks good, now create the serverless resources
Agent: [Creates namespace and workgroup]

You: Apply the configuration
Agent: [Applies config]

You: save
💾 Conversation saved!

You: exit
```

## Integration with Other Tools

### Save Output to File

```bash
python3 chat_with_agent.py | tee migration_session.log
```

### Use in Scripts

```python
import boto3
import json

lambda_client = boto3.client('lambda', region_name='us-east-2')

response = lambda_client.invoke(
    FunctionName='redshift-migration-agent',
    Payload=json.dumps({'message': 'List my clusters'})
)

result = json.loads(response['Payload'].read())
print(json.loads(result['body'])['response'])
```

## Next Steps

1. Start chatting: `python3 chat_with_agent.py`
2. Ask the agent what it can do
3. Try a test migration on a non-production cluster
4. Review saved conversations to track your work

## Need Help?

- Ask the agent: Type `help` in the chat
- Check logs: `./check_lambda_logs.sh`
- GitHub Issues: https://github.com/milindoke/redshift-migration-agent/issues

---

**Ready to chat?** Run: `python3 chat_with_agent.py`

Enjoy natural conversations with your migration agent! 🚀
