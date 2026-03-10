# Redshift Modernization Agents

Multi-agent system for comprehensive Amazon Redshift cluster modernization using AWS Transform (ATX) BaseAgent SDK.

## Status: Ready for Bedrock Deployment 🚀

✅ All container images built and pushed to ECR
✅ Ready to deploy to Bedrock AgentCore

See [ECR_PUSH_SUCCESS.md](./ECR_PUSH_SUCCESS.md) for deployment instructions.

## What This Does

Guides customers through complete Redshift modernization with AI agents:
- **Assessment**: Analyzes cluster configuration and performance
- **Scoring**: Evaluates best practices (Security 35%, Performance 35%, Cost 30%)
- **Architecture**: Designs multi-warehouse architectures
- **Execution**: Creates phased migration plans

## Architecture

All agents run within the customer account:

```
Customer Account (<ACCOUNT_ID>)
┌─────────────────────────────────────────────────────────────┐
│   Orchestrator Agent                                        │
│   • Coordinates workflow                                    │
│   • Delegates to subagents via ATX MCP                      │
│                                                             │
│   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│   │ Assessment   │ │ Scoring      │ │ Architecture │       │
│   │ • Cluster    │ │ • Best       │ │ • Multi-WH   │       │
│   │   analysis   │ │   practices  │ │   design     │       │
│   │ • Metrics    │ │   evaluation │ │              │       │
│   └──────────────┘ └──────────────┘ └──────────────┘       │
│   ┌──────────────┐                                          │
│   │ Execution    │                                          │
│   │ • Migration  │                                          │
│   │   planning   │                                          │
│   └──────────────┘                                          │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

- AWS CLI configured for the customer account
- Python 3.12+
- ATX credentials (workspace ID, auth token)
- BaseAgent SDK (automatically available via pip with atx-dev power)

## Quick Start

### Deploy with Finch

```bash
cd src/redshift_agents
./deploy-with-finch.sh
```

### Unit Tests (Local, no AWS credentials needed)

```bash
pip install -r tests/requirements-test.txt
pytest tests/ -v
```

### Test Full Workflow

```bash
atx-cli invoke-agent \
  --agent-id redshift-orchestrator \
  --message "Modernize cluster prod-cluster-01 in us-east-2" \
  --customer-account-id <ACCOUNT_ID>
```

## Configuration

### Environment Variables

All agents:
```
AWS_REGION=us-east-2
STORAGE_DIR=/tmp/<agent-name>
```

Orchestrator additionally:
```
WORKSPACE_ID=<your-workspace-id>
MCP_AUTH_TOKEN=<your-auth-token>
```

### IAM Role

Single role for all agents with:
- Redshift: DescribeClusters (read-only)
- CloudWatch: GetMetricStatistics (read-only), Logs write
- Bedrock: InvokeAgent (orchestrator)
- S3: Read/Write for conversation storage (orchestrator)
- ECR: Pull images

## Project Structure

```
src/redshift_agents/
├── orchestrator/              # Orchestrator agent
│   └── orchestrator.py
├── subagents/                 # Specialized subagents
│   ├── assessment.py
│   ├── scoring.py
│   ├── architecture.py
│   └── execution.py
├── tools/                     # Redshift analysis tools
│   └── redshift_tools.py
├── tests/                     # Unit tests
│   ├── test_redshift_tools.py
│   └── requirements-test.txt
├── docs/                      # Deployment checklist, testing guide
├── docker/                    # Dockerfiles + docker-compose
├── requirements.txt
└── .env.example
```

## Key Features

- ✅ Single-account deployment (all agents in customer account)
- ✅ Conversation isolation (namespace-based sessions)
- ✅ Best practices scoring (Security 35%, Performance 35%, Cost 30%)
- ✅ 5-phase migration planning
- ✅ Multi-warehouse architecture design

## Monitoring

```bash
# Agent logs
aws logs tail /aws/bedrock/agentcore/redshift-orchestrator --follow
aws logs tail /aws/bedrock/agentcore/redshift-assessment-subagent --follow
```

## Documentation

- [ECR Push Success](./ECR_PUSH_SUCCESS.md) — Current status & next steps
- [Deployment Checklist](./docs/deployment-checklist.md) — Step-by-step deployment
- [Testing Guide](./docs/testing.md) — Testing strategies
