# Deploying the Redshift Migration Strand Agent

This guide explains how to deploy the Redshift Migration Assistant as a standalone Strand agent.

## Overview

The agent (`redshift_agent.py`) is a conversational AI assistant that helps users migrate from AWS Redshift Provisioned clusters to Serverless. It uses the Strands SDK with Amazon Bedrock to provide an interactive experience.

## Prerequisites

1. **AWS Account** with:
   - Redshift provisioned cluster access
   - Permissions to create Redshift Serverless resources
   - Bedrock API access

2. **Python 3.8+** installed

3. **AWS Credentials** configured (one of):
   - Bedrock API key (recommended for development)
   - AWS credentials via `aws configure`
   - Environment variables

## Installation

### Step 1: Install the Migration Tool

```bash
# Install the redshift-migrate CLI tool
pip install -e .

# Verify installation
redshift-migrate --help
```

### Step 2: Install Strand Agent Dependencies

```bash
# Install Strands SDK and tools
pip install -r requirements-agent.txt
```

### Step 3: Configure AWS Credentials

#### Option A: Bedrock API Key (Recommended for Development)

1. Open [Bedrock Console](https://console.aws.amazon.com/bedrock) → API keys
2. Generate a long-term API key (30 days)
3. Set environment variable:

```bash
export AWS_BEDROCK_API_KEY=your_bedrock_api_key
```

#### Option B: AWS Credentials (Production)

```bash
# Configure AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

### Step 4: Enable Model Access in Bedrock

1. Open [Bedrock Console](https://console.aws.amazon.com/bedrock)
2. Navigate to "Model access" in left sidebar
3. Click "Manage model access"
4. Enable "Claude 4 Sonnet" (anthropic.claude-sonnet-4-20250514-v1:0)
5. Wait a few minutes for access to propagate

## Running the Agent

### Interactive Mode

Run the agent in conversational mode:

```bash
python redshift_agent.py
```

Example conversation:
```
You: I need to migrate my cluster prod-cluster-1 in us-east-1 to serverless