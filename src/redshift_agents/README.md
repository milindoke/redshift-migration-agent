# Redshift Modernization Agents

Multi-agent system for migrating Amazon Redshift Provisioned clusters to Serverless using the Strands Agent framework and Amazon Bedrock AgentCore.

## What This Does

- **3-phase workflow**: Assessment → Architecture → Execution with approval gates between each phase
- **WLM queue analysis**: Surfaces contention problems (wait times, disk spill, queue saturation) to build the case for multi-warehouse migration
- **Workgroup split design**: Maps WLM queues to Serverless workgroups with RPU sizing (minimum 32 for AI-driven scaling)
- **Automated execution**: Creates namespaces/workgroups, restores snapshots, sets up data sharing, migrates users, validates performance
- **Two migration paths**: Multi-workgroup split (contention-driven) or 1:1 migration (purpose-built clusters)

## Architecture

```
Customer Account
┌──────────────────────────────────────────────────────────────┐
│  Orchestrator Agent                                          │
│  • 3-phase workflow coordination                             │
│  • Approval gates (human-in-the-loop)                        │
│  • Cluster locking (DynamoDB)                                │
│  • Identity propagation                                      │
│                                                              │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐    │
│  │ Assessment     │ │ Architecture   │ │ Execution      │    │
│  │ • Cluster      │ │ • Workgroup    │ │ • Create ns/wg │    │
│  │   discovery    │ │   split design │ │ • Snapshot      │    │
│  │ • WLM queue    │ │ • RPU sizing   │ │   restore      │    │
│  │   analysis     │ │   (≥32 RPU)    │ │ • Data sharing │    │
│  │ • CloudWatch   │ │ • Diagnostic   │ │ • User migrate │    │
│  │   metrics      │ │   SQL          │ │ • Validation   │    │
│  └────────────────┘ └────────────────┘ └────────────────┘    │
│                                                              │
│  Shared Tools (@tool) ──► Redshift, CloudWatch, DynamoDB     │
│  Audit Logger ──► CloudWatch Logs                            │
└──────────────────────────────────────────────────────────────┘
```

All agents run within the customer account. No cross-account dependencies. Customer data never leaves the account.

## Quick Start

### 1. Deploy Agents to Bedrock AgentCore

```bash
cd src/redshift_agents
./deploy-agentcore.sh
```

This runs `agentcore launch` for each agent (orchestrator + 3 subagents).

### 2. Launch the Chat UI

```bash
pip install -r ui/requirements.txt
export ORCHESTRATOR_AGENT_ID=<your-agent-id>
streamlit run ui/app.py
```

Opens a chat interface at `http://localhost:8501` where you can interact with the orchestrator conversationally.

### Run Unit Tests (no AWS credentials needed)

```bash
pip install -r src/redshift_agents/tests/requirements-test.txt
cd src/redshift_agents
pytest tests/ -v
```

### Configuration

Copy `.env.example` and set your values:

```bash
cp .env.example .env
```

Key variables:

| Variable | Description |
|----------|-------------|
| `AWS_REGION` | Deployment region (agents can operate on clusters in any region) |
| `DYNAMODB_LOCK_TABLE` | DynamoDB table name for cluster locking |
| `ASSESSMENT_AGENT_ID` | Bedrock AgentCore agent ID (set after deployment) |
| `ARCHITECTURE_AGENT_ID` | Bedrock AgentCore agent ID (set after deployment) |
| `EXECUTION_AGENT_ID` | Bedrock AgentCore agent ID (set after deployment) |

## Workflow

### Phase 1: Assessment

The assessment agent analyzes the target Redshift Provisioned cluster:
- Discovers clusters in the account (or uses a specified cluster ID)
- Retrieves cluster configuration (node type, count, encryption, VPC, enhanced VPC routing)
- Pulls CloudWatch metrics (CPU, connections, network, disk, latency)
- Queries WLM configuration and per-queue metrics (wait times, disk spill, saturation)
- Produces a contention narrative explaining why migration is needed

### Gate 1: Approval

Assessment results are presented to the user. The orchestrator **will not proceed** until the user explicitly approves.

### Phase 2: Architecture

The architecture agent designs the target Serverless topology:
- Maps WLM queues to Serverless workgroups (multi-queue → one workgroup per queue; single queue → producer/consumer split)
- Runs diagnostic SQL to determine starting RPU values (minimum 32 RPU)
- Recommends AI-driven scaling with price-performance targets
- Supports three patterns: hub-and-spoke (data sharing), independent warehouses, hybrid
- Includes cost estimates and migration complexity assessment

### Gate 2: Approval

The proposed architecture is presented to the user. The orchestrator **will not proceed** until the user explicitly approves.

### Phase 3: Execution

The execution agent carries out the migration:
- Creates Serverless namespace and workgroups per the architecture spec
- Restores a snapshot of the Provisioned cluster into the new namespace
- Sets up data sharing between workgroups (if hub-and-spoke)
- Generates a user/application migration plan (old WLM queues → new workgroups)
- Validates query performance on new workgroups
- Defines rollback procedures at each step
- Plans minimal/zero downtime cutover

## Cluster Locking

A DynamoDB table (`redshift_modernization_locks`) prevents two users from working on the same cluster simultaneously.

- Lock acquired at workflow start, released on completion or failure
- Uses DynamoDB conditional writes for atomic acquisition
- Locks auto-expire after 24 hours (TTL) as a safety net
- If a cluster is locked, the user is told who holds the lock and when it was acquired

## Identity Propagation

The identity of the person who initiated a request is propagated end-to-end:

```
User (jane.doe)
  → Orchestrator session (user_id="jane.doe")
    → Subagent payload (user_id="jane.doe")
      → Tool invocation (audit: initiated_by="jane.doe")
        → Redshift Data API (DbUser="jane.doe")
          → Redshift audit logs (STL_CONNECTION_LOG)
            → CloudTrail (PrincipalTag/user=jane.doe)
```

Every audit log event, every SQL query, and every CloudTrail entry traces back to the individual who triggered the workflow.

## IAM Roles

Each agent has its own least-privilege IAM role:

| Agent | Key Permissions |
|-------|----------------|
| Orchestrator | `bedrock:InvokeAgent`, DynamoDB read/write (locks), CloudWatch Logs |
| Assessment | `redshift:Describe*`, `redshift-data:ExecuteStatement` (read-only), `cloudwatch:GetMetricStatistics` |
| Architecture | `redshift:Describe*`, `redshift-data:ExecuteStatement` (diagnostic SQL), `cloudwatch:GetMetricStatistics` |
| Execution | `redshift-serverless:Create*`, `redshift-serverless:Update*`, `redshift:RestoreFromClusterSnapshot`, `redshift-data:ExecuteStatement` |

IAM policy files are in `iam/`.

## Project Structure

```
src/redshift_agents/
├── orchestrator/
│   └── orchestrator.py          # Orchestrator agent (workflow, locking, gates)
├── subagents/
│   ├── assessment.py            # Cluster analysis + WLM queue metrics
│   ├── architecture.py          # Workgroup split design + RPU sizing
│   └── execution.py             # Migration execution + validation
├── tools/
│   ├── redshift_tools.py        # Shared @tool functions (boto3 calls)
│   ├── cluster_lock.py          # DynamoDB cluster locking
│   ├── audit_logger.py          # Structured JSON audit logging
│   └── log_sharing.py           # Cross-account log sharing (opt-in)
├── ui/
│   ├── app.py                   # Streamlit chat UI
│   ├── requirements.txt         # UI dependencies
│   └── README.md                # UI setup instructions
├── iam/                         # Per-agent IAM policy documents
├── tests/                       # Unit tests (pytest, no AWS creds needed)
│   ├── conftest.py
│   ├── test_redshift_tools.py
│   ├── test_assessment.py
│   ├── test_architecture.py
│   ├── test_execution.py
│   ├── test_orchestrator.py
│   ├── test_cluster_lock.py
│   ├── test_audit_logger.py
│   └── requirements-test.txt
├── models.py                    # Data models (dataclasses)
├── deploy-agentcore.sh          # Deploy all agents via agentcore launch
├── requirements.txt
└── .env.example
```

## Monitoring

```bash
# Agent logs
aws logs tail /aws/bedrock/agentcore/redshift-orchestrator --follow
aws logs tail /aws/bedrock/agentcore/redshift-assessment --follow
aws logs tail /aws/bedrock/agentcore/redshift-architecture --follow
aws logs tail /aws/bedrock/agentcore/redshift-execution --follow
```
