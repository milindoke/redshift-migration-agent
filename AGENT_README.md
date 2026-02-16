# Redshift Migration Strand Agent

A conversational AI agent that helps you migrate from AWS Redshift Provisioned clusters to Redshift Serverless.

## Quick Start

### 1. Deploy the Agent

```bash
./deploy_agent.sh
```

This will:
- Install the redshift-migrate CLI tool
- Install Strands SDK dependencies
- Verify AWS credentials
- Test the agent

### 2. Set Up AWS Credentials

Choose one option:

**Option A: Bedrock API Key (Easiest)**
```bash
export AWS_BEDROCK_API_KEY=your_bedrock_api_key
```

Get your key from: https://console.aws.amazon.com/bedrock → API keys

**Option B: AWS Credentials**
```bash
aws configure
# or
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

### 3. Enable Bedrock Model Access

1. Go to https://console.aws.amazon.com/bedrock
2. Click "Model access" → "Manage model access"
3. Enable "Claude 4 Sonnet"
4. Wait 2-3 minutes

### 4. Run the Agent

```bash
python redshift_agent.py
```

## Usage Examples

### Interactive Conversation

```
You: I need to migrate my cluster prod-db-1 in us-east-1