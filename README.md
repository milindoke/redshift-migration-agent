# Redshift Migration Agent 🚀

AI-powered agent to migrate AWS Redshift Provisioned clusters to Serverless with zero downtime.

> **🆕 NEW: ATX Multi-Agent Architecture** - Now includes a production-ready multi-agent system for comprehensive Redshift modernization using AWS Transform (ATX) framework. See [ATX Implementation](#-atx-multi-agent-architecture) below.

[![GitHub release](https://img.shields.io/github/v/release/milindoke/redshift-migration-agent)](https://github.com/milindoke/redshift-migration-agent/releases)
[![Deploy to AWS](https://img.shields.io/badge/Deploy%20to-AWS-orange?logo=amazon-aws)](https://github.com/milindoke/redshift-migration-agent)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

[![GitHub stars](https://img.shields.io/github/stars/milindoke/redshift-migration-agent?style=social)](https://github.com/milindoke/redshift-migration-agent/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/milindoke/redshift-migration-agent?style=social)](https://github.com/milindoke/redshift-migration-agent/network/members)
[![GitHub issues](https://img.shields.io/github/issues/milindoke/redshift-migration-agent)](https://github.com/milindoke/redshift-migration-agent/issues)

## 🎯 What It Does

This AI agent helps you migrate from AWS Redshift Provisioned clusters to Redshift Serverless by:

- ✅ Extracting all cluster configurations automatically
- ✅ Creating snapshots and restoring to Serverless
- ✅ Migrating IAM roles, VPC settings, and security groups
- ✅ Mapping parameter groups to Serverless equivalents
- ✅ Migrating scheduled queries from EventBridge to Serverless
- ✅ Carrying over maintenance track and cross-region snapshot copy settings
- ✅ Migrating usage limits with intelligent recommendations for Serverless
- ✅ Detecting multiple WLM queues and offering single or multi-workgroup migration
- ✅ **Persistent memory across hours/days** - Agent remembers your migrations
- ✅ Providing conversational guidance throughout the process

## 🤖 AI-Driven Scaling & Cost Optimization

The agent leverages the latest **AI-driven scaling features** of Amazon Redshift Serverless:

- **Price-Performance Targets**: Automatically configures workgroups with balanced (50) price-performance settings
- **Smart Cost Controls**: Sets MaxRPU limits automatically to prevent runaway costs
- **Intelligent Scaling**: Redshift AI continuously optimizes compute resources based on workload patterns
- **Zero Manual Tuning**: No need to manually adjust capacity - AI handles it for you

This means your migrated workloads get optimal performance at the lowest cost, automatically.

## 🚀 Quick Deploy (3 Minutes)

### One-Command Deploy

```bash
# Clone the repository
git clone https://github.com/milindoke/redshift-migration-agent.git
cd redshift-migration-agent

# Deploy (that's it!)
./deploy
```

### Manual Deploy

```bash
# Using SAM CLI
sam build
sam deploy --guided
```

See [Deployment Guide](docs/deployment/DEPLOY_NOW.md) for detailed instructions.

## 💬 How to Use

### Natural Conversation Interface (Recommended)

```bash
# Start chatting with the agent
./chat
```

Then just ask naturally:
```
You: List my Redshift clusters in us-east-2
Agent: [Shows clusters]

You: Tell me about the first one
Agent: [Shows details]

You: Migrate it to serverless
Agent: [Guides through migration]
```

See [Chat Guide](docs/guides/START_CHATTING.md) for more.

### Via AWS CLI

```bash
# Simple usage - memory enabled automatically
aws lambda invoke \
  --function-name redshift-migration-agent \
  --cli-binary-format raw-in-base64-out \
  --payload '{"message":"List my Redshift clusters in us-east-2"}' \
  response.json

cat response.json

# Use with custom session_id for long-running migrations
aws lambda invoke \
  --function-name redshift-migration-agent \
  --payload '{
    "message":"Start migration for prod-cluster",
    "session_id":"prod-migration-jan2024"
  }' \
  response.json

# Continue later - agent remembers everything from the same session
aws lambda invoke \
  --function-name redshift-migration-agent \
  --payload '{
    "message":"What was the status?",
    "session_id":"prod-migration-jan2024"
  }' \
  response.json
```

Memory is enabled by default - the agent automatically remembers conversations within a session.

### 🧠 How Memory & Conversation Management Works

The agent uses two complementary systems to maintain context:

1. **Long-term Memory (AgentCore Memory)**
   - Stores summaries, facts, and preferences across sessions
   - Persists for hours/days - come back anytime with the same `session_id`
   - Automatically extracts key information from conversations
   - Enables the agent to remember migration progress and decisions

2. **Sliding Window (Recent Messages)**
   - Keeps the last 10 messages in active context
   - Prevents context overflow in tool-heavy conversations
   - Automatically truncates large tool results
   - Very conservative window size to maintain toolUse/toolResult balance

This dual approach means:
- ✅ Agent remembers important details across sessions
- ✅ Tool-heavy conversations work smoothly
- ✅ No manual intervention needed
- ✅ Context stays relevant and focused

**Note:** In extremely long conversations with many tool calls (30+ messages), you may need to start a new session. The chat script will automatically detect this and prompt you to start fresh. Don't worry - important information is preserved in long-term memory!

## 🎬 Example Conversations

```
You: "List all my Redshift clusters in us-east-2"
Agent: [Lists all clusters with details]

You: "Extract configuration from cluster prod-db-1"
Agent: [Extracts IAM roles, VPC, parameters, etc.]

You: "List scheduled queries for prod-db-1"
Agent: [Shows all EventBridge scheduled queries]

You: "Migrate cluster prod-db-1 to serverless with snapshot"
Agent: [Guides through migration process]

You: "Migrate scheduled queries from prod-db-1 to my-serverless-wg"
Agent: [Migrates all scheduled queries to serverless workgroup]

You: "Get snapshot copy settings for prod-db-1"
Agent: [Shows cross-region snapshot copy configuration]

You: "Configure snapshot copy for my-namespace to us-west-2 with 7 day retention"
Agent: [Configures cross-region snapshot copy for serverless]

You: "Get usage limits for prod-db-1"
Agent: [Shows usage limits configured on the cluster]

You: "Migrate usage limits from prod-db-1 to my-serverless-wg"
Agent: [Provides recommendations for serverless usage limits]

You: "Get WLM queues for prod-db-1"
Agent: [Shows WLM queue configuration]

You: "Create multiple workgroups from WLM queues for prod-db-1"
Agent: [Creates one workgroup per WLM queue for workload isolation]

You: "What's the status of my migration?"
Agent: [Checks and reports status]
```

## 🏗️ Architecture

### Lambda-Based Migration Agent (Current)
```
User Request
    ↓
AWS Lambda (Agent)
    ↓
Amazon Bedrock (Claude AI)
    ↓
AWS Redshift APIs
    ↓
Migration Complete
```

### 🆕 ATX Multi-Agent Architecture (New)

For comprehensive Redshift modernization with cross-account security:

```
Service Account (Orchestrator)  ←→  Customer Account (4 Subagents)
     No Cluster Access                  Direct Cluster Access
```

**Branch**: `atx-redshift-modernization-agent`

See [ATX Implementation](#-atx-multi-agent-architecture) section below for details.

## 💰 Cost Estimate

- **Lambda**: ~$0-20/month (pay per request)
- **Bedrock**: ~$3-10/month (based on usage)
- **Total**: ~$5-30/month

First 1M Lambda requests are free!

## 🔒 Security

- ✅ IAM authentication required
- ✅ No public access
- ✅ Least privilege permissions
- ✅ CloudWatch logging
- ✅ Audit trail via CloudTrail

## 📋 Prerequisites

- AWS Account
- IAM permissions to deploy Lambda and create IAM roles
- Bedrock model access enabled (Claude Sonnet 4.5)

### Enable Bedrock Access

1. Go to [Bedrock Console](https://console.aws.amazon.com/bedrock)
2. Click "Model access"
3. Enable "Claude 4.5 Sonnet"
4. Wait 2-3 minutes

## 🛠️ Features

### Automated Configuration Extraction
- IAM roles and default role designation
- VPC configuration (subnets, security groups)
- Parameter groups (10+ parameters)
- Scheduled queries (EventBridge Rules & Scheduler)
- Snapshot schedules
- Tags and logging

### Intelligent Migration
- Automatic snapshot creation
- Smart parameter mapping
- VPC and security group migration
- Scheduled query migration to serverless workgroups
- Price-performance optimization

### Scheduled Query Migration
- Extract queries from EventBridge Rules and Scheduler
- Recreate queries to target serverless workgroups
- Preserve schedule expressions and query logic
- Automatic IAM role creation for query execution
- Dry-run mode to preview changes

### Maintenance and Snapshot Settings
- Extract maintenance track and window from provisioned clusters
- Get cross-region snapshot copy configuration
- Configure snapshot copy for serverless namespaces
- Preserve retention periods and KMS encryption settings
- Note: Serverless uses automatic maintenance (no manual windows)

### Usage Limits
- Extract usage limits from provisioned clusters (spectrum, concurrency-scaling, datasharing)
- Get intelligent recommendations for serverless limits (RPU-hours)
- Create usage limits for serverless workgroups
- Support for daily, weekly, and monthly periods
- Configurable breach actions (log, emit-metric, deactivate)

### WLM Queue Migration
- Detect multiple WLM queues in provisioned clusters
- Ask user: single workgroup or multiple workgroups?
- Create one workgroup per WLM queue for workload isolation
- Automatic workgroup sizing based on queue concurrency
- Naming convention: {cluster-id}-{queue-name}
- All workgroups share the same namespace (data)

### Conversational Interface
- Natural language queries
- Step-by-step guidance
- Error explanation and troubleshooting
- Best practice recommendations

## 📚 Documentation

- [Quick Start - Chat Interface](docs/guides/START_CHATTING.md) - Start here!
- [Deployment Guide](docs/deployment/DEPLOY_NOW.md) - Deploy the agent
- [Chat Guide](docs/guides/CHAT_GUIDE.md) - Complete chat documentation
- [Scheduled Query Migration](docs/guides/SCHEDULED_QUERIES.md) - Migrate scheduled queries
- [Maintenance & Snapshot Settings](docs/guides/MAINTENANCE_AND_SNAPSHOTS.md) - Migrate maintenance and snapshot copy
- [Usage Limits Migration](docs/guides/USAGE_LIMITS.md) - Migrate and configure usage limits
- [WLM Queue Migration](docs/guides/WLM_QUEUES.md) - Handle multiple WLM queues
- [Security Setup](docs/guides/SECURE_ACCESS.md) - IAM and access control
- [Project Structure](PROJECT_STRUCTURE.md) - Navigate the codebase
- [Migration Patterns](docs/QUICKSTART.md) - Common migration scenarios
- [Troubleshooting](docs/deployment/TROUBLESHOOT_LAMBDA.md) - Fix common issues

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md)

## 📝 License

MIT License - see [LICENSE](LICENSE)

## 🆘 Support

- 📖 [Documentation](docs/)
- 🐛 [Report Issues](https://github.com/milindoke/redshift-migration-agent/issues)
- 💬 [Discussions](https://github.com/milindoke/redshift-migration-agent/discussions)

## 🌟 Star History

If this project helped you, please ⭐ star it on GitHub!

## 📊 Stats

- ⚡ Average migration time: 15-30 minutes
- 🎯 Success rate: 95%+
- 💾 Supports clusters up to 100+ nodes
- 🌍 Available in all AWS regions

## 🔗 Related Projects

- [AWS Redshift Documentation](https://docs.aws.amazon.com/redshift/)
- [Strands Agents SDK](https://github.com/strands-agents/sdk-python)
- [Amazon Bedrock](https://aws.amazon.com/bedrock/)

---

## 🏢 ATX Multi-Agent Architecture

### Overview

A production-ready multi-agent system for comprehensive Redshift modernization using AWS Transform (ATX) framework. This implementation uses a cross-account architecture for maximum security and compliance.

### Architecture

**Service Account** (Orchestrator):
- Coordinates modernization workflow
- Maintains conversation state
- NO direct access to customer clusters

**Customer Account** (4 Subagents):
- Assessment: Analyzes cluster configuration
- Scoring: Evaluates best practices (0-100 score, A-F grade)
- Architecture: Designs multi-warehouse topology
- Execution: Creates phased implementation plan

### Key Features

✅ **Cross-Account Security**: Customer data never leaves customer account  
✅ **Best Practices Scoring**: Automated evaluation against AWS standards  
✅ **Multi-Warehouse Design**: Workload separation and data sharing strategies  
✅ **Phased Migration**: 5-phase implementation plan (12-18 weeks)  
✅ **Production Ready**: Built on ATX BaseAgent SDK with Strands framework  

### Quick Start

```bash
# Switch to ATX branch
git checkout atx-redshift-modernization-agent

# Local testing
cd src/atx_agents
python -m orchestrator.orchestrator_cli --local-testing

# Try it
> Analyze my Redshift cluster 'my-cluster-id'
> Design a multi-warehouse architecture
```

### Documentation

- **[ATX Implementation Summary](ATX_IMPLEMENTATION_SUMMARY.md)** - Complete overview
- **[Cross-Account Deployment](src/atx_agents/CROSS_ACCOUNT_DEPLOYMENT.md)** - Production deployment
- **[Architecture Details](src/atx_agents/ARCHITECTURE.md)** - System design
- **[Quick Start](src/atx_agents/QUICK_START.md)** - Get started in 5 minutes
- **[Deployment Checklist](src/atx_agents/DEPLOYMENT_CHECKLIST.md)** - Step-by-step guide

### Benefits

**vs. Lambda Agent**:
- Multi-agent coordination for complex workflows
- Stateful conversation management
- Cross-account security model
- Production-grade infrastructure

**vs. Manual Modernization**:
- Automated assessment and scoring
- Best practices built-in
- Consistent methodology
- Faster time to value

### Deployment

**Service Account** (Redshift Service Team):
```bash
cd src/atx_agents/orchestrator
docker build -t orchestrator:latest .
# Deploy to ECS in service account
```

**Customer Account**:
```bash
cd src/atx_agents/subagents
# Build and deploy all 4 subagents to customer account
```

See [Cross-Account Deployment Guide](src/atx_agents/CROSS_ACCOUNT_DEPLOYMENT.md) for complete instructions.

### Use Cases

1. **Comprehensive Assessment**: Analyze cluster configuration, performance, and usage patterns
2. **Best Practices Evaluation**: Get scored on security, performance, and cost optimization
3. **Architecture Design**: Design multi-warehouse topology with workload separation
4. **Phased Migration**: Execute 12-18 week implementation plan with validation

### Technology Stack

- Python 3.11+
- AWS Transform (ATX) BaseAgent SDK
- Strands Framework
- ECS Fargate
- Cross-account IAM roles

---

**Made with ❤️ for the AWS community**

Deploy now and start migrating! 🚀
