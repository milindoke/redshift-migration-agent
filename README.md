# Redshift Modernization Agents 🚀

AI-powered multi-agent system for migrating Amazon Redshift Provisioned clusters to Serverless, built on fully managed Amazon Bedrock Agents.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

## What It Does

The system walks you through a 3-phase modernization workflow with human-in-the-loop approval gates:

1. **Assessment** — Analyzes cluster configuration, CloudWatch metrics, and WLM queue contention (wait times, disk spill, saturation per service class)
2. **Architecture Design** — Designs Serverless workgroup topology: WLM-to-workgroup mapping, RPU sizing, three patterns (hub-and-spoke, independent, hybrid), cost estimates
3. **Execution** — Creates namespaces/workgroups, restores snapshots, sets up data sharing, validates performance, plans cutover

Two migration paths:
- **Multi-workgroup split** — when WLM contention justifies separating workloads
- **1:1 migration** — when a single Serverless workgroup suffices

## Architecture

```
User (Streamlit UI + Cognito auth)
        │
        ▼
Orchestrator Agent  ──── cluster lock (DynamoDB)
        │                list clusters (Lambda)
        ├──▶ Assessment Agent  ──── assessment-tools Lambda
        │                           (analyzeCluster, getMetrics, getWlmConfig)
        │
        ├──▶ Architecture Agent ─── assessment + execution Lambdas
        │                           + Bedrock Knowledge Base (S3 Vectors)
        │
        └──▶ Execution Agent ────── execution-tools Lambda
                                    (snapshot, restore, serverless, data sharing)
```

**4 Bedrock Agents** (supervisor + 3 collaborators), all within your AWS account. No cross-account dependencies, no service accounts.

### Key Features

- **One-click deploy** — single `cdk deploy` provisions everything: Lambda functions, Bedrock Agents, Knowledge Base, DynamoDB, Cognito, IAM roles
- **Cluster-level memory** — agents remember previous conversations per cluster (30-day SESSION_SUMMARY retention); any user on the same cluster sees shared history
- **Agent reasoning trace** — the UI surfaces the agent's thinking: rationale, tool calls, sub-agent delegation, and KB lookups in a collapsible expander per response
- **Forget cluster memory** — one-click button wipes SESSION_SUMMARY across all 4 agents for the active cluster
- **WLM analysis** — queries service classes 6–13 (manual WLM) and 100–107 (auto WLM) for contention metrics
- **End-to-end identity** — `user_id` flows from UI → orchestrator → sub-agent → tool → Redshift Data API → CloudTrail
- **Approval gates** — orchestrator will not advance phases without explicit user confirmation
- **Cognito auth** — self-registration disabled; admin-created users only; UI shows email not UUID

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agents | Amazon Bedrock Agents (CfnAgent, supervisor/collaborator) |
| Knowledge Base | Bedrock KB with S3 Vectors storage + Titan Embed v2 |
| Infrastructure | AWS CDK (Python), container runtime: Finch |
| Lambda runtime | Python 3.12 |
| UI | Streamlit + Cognito USER_PASSWORD_AUTH |
| Lock store | DynamoDB (TTL-based cluster locks) |
| Audit | Structured JSON logging via `python-json-logger` |

## AWS Services Required

Check availability in your target region before deploying:

| Service | Usage |
|---------|-------|
| **Amazon Bedrock** | Agents (supervisor + 3 collaborators), Knowledge Base, foundation model inference |
| **Amazon Bedrock — Claude 3.5 Sonnet v2** | `anthropic.claude-3-5-sonnet-20241022-v2:0` — all 4 agents |
| **Amazon Bedrock — Titan Embed v2** | `amazon.titan-embed-text-v2:0` — KB document embedding |
| **Amazon S3 Vectors** | Vector bucket + index for Knowledge Base storage (`AWS::S3Vectors::VectorBucket`) |
| **Amazon S3** | KB source document storage |
| **AWS Lambda** | Action group handlers (assessment, execution, cluster-lock) |
| **Amazon DynamoDB** | Cluster-level locking table |
| **Amazon Cognito** | User Pool (auth) + Identity Pool (temporary AWS credentials for UI) |
| **Amazon Redshift** | Source provisioned clusters being assessed and migrated |
| **Amazon Redshift Serverless** | Target namespaces and workgroups created during execution |
| **Amazon Redshift Data API** | SQL execution for WLM analysis and query tools |
| **Amazon CloudWatch** | Cluster performance metrics (CPU, connections, disk, latency) |
| **AWS CloudFormation** | CDK stack deployment |
| **AWS IAM** | Roles for Lambda, Bedrock Agents, Cognito Identity Pool |
| **AWS Secrets Manager** | Admin password management for Serverless namespaces |

> **Tip:** Before deploying, verify Bedrock model access for `anthropic.claude-3-5-sonnet-20241022-v2:0` and `amazon.titan-embed-text-v2:0` is enabled in your region. S3 Vectors is a newer service — confirm it is available in your region via the [AWS Regional Services list](https://aws.amazon.com/about-aws/global-infrastructure/regional-product-services/).

## IAM Permissions

CDK creates all roles automatically. This section documents exactly what each role is allowed to do — no surprises.

### Assessment Lambda role

Invoked by the Assessment and Architecture agents to analyze clusters and retrieve WLM metrics.

| Permission | Resource | Why |
|------------|----------|-----|
| `redshift:DescribeClusters` | `*` | List and inspect provisioned clusters |
| `redshift-data:ExecuteStatement` | `*` | Run WLM diagnostic SQL via Data API |
| `redshift-data:DescribeStatement` | `*` | Poll statement execution status |
| `redshift-data:GetStatementResult` | `*` | Fetch WLM query results |
| `redshift:GetClusterCredentialsWithIAM` | `*` | IAM-based auth for Data API calls |
| `cloudwatch:GetMetricStatistics` | `*` | Retrieve CPU, connections, disk, latency metrics |
| `logs:CreateLogGroup/Stream`, `logs:PutLogEvents` | Lambda log group | Lambda basic execution (managed policy) |

### Execution Lambda role

Invoked by the Execution and Architecture agents to create Serverless resources and run migration steps.

| Permission | Resource | Why |
|------------|----------|-----|
| `AmazonRedshiftFullAccess` (managed policy) | `*` | Create snapshots, namespaces, workgroups, restore, data sharing, Data API |
| `secretsmanager:*` | `*` | Manage admin password when creating Serverless namespaces (`manageAdminPassword=True`) |
| `logs:CreateLogGroup/Stream`, `logs:PutLogEvents` | Lambda log group | Lambda basic execution (managed policy) |

> `AmazonRedshiftFullAccess` is broad by design — the execution phase needs to create and configure Serverless resources. If your security posture requires tighter scoping, you can replace it with explicit `redshift:CreateClusterSnapshot`, `redshift-serverless:CreateNamespace/Workgroup`, `redshift-data:*`, and `redshift-serverless:RestoreFromSnapshot` actions.

### Cluster Lock Lambda role

Invoked by the Orchestrator agent to acquire and release cluster-level locks.

| Permission | Resource | Why |
|------------|----------|-----|
| `dynamodb:PutItem` | Lock table ARN only | Acquire lock (conditional write) |
| `dynamodb:DeleteItem` | Lock table ARN only | Release lock |
| `dynamodb:GetItem` | Lock table ARN only | Read current lock holder on contention |
| `logs:CreateLogGroup/Stream`, `logs:PutLogEvents` | Lambda log group | Lambda basic execution (managed policy) |

### Bedrock Agent roles (all 4 agents)

Each agent has its own IAM role trusted by `bedrock.amazonaws.com`.

| Permission | Resource | Why |
|------------|----------|-----|
| `bedrock:InvokeModel` | `anthropic.claude-*` foundation models | Run LLM inference |
| `bedrock:InvokeModelWithResponseStream` | `anthropic.claude-*` foundation models | Streaming inference |
| `lambda:InvokeFunction` | Specific Lambda ARNs only | Invoke action group handlers |
| `bedrock:InvokeAgent` | `*` | Orchestrator delegates to sub-agents |
| `bedrock:GetAgent`, `bedrock:GetAgentAlias` | `*` | Orchestrator resolves sub-agent aliases |
| `bedrock:Retrieve`, `bedrock:RetrieveAndGenerate` | Architecture KB ARN only | Architecture agent queries the KB |

### Knowledge Base role

Trusted by `bedrock.amazonaws.com` for KB ingestion and retrieval.

| Permission | Resource | Why |
|------------|----------|-----|
| `s3:GetObject`, `s3:ListBucket` | KB source S3 bucket | Read architecture docs for embedding |
| `bedrock:InvokeModel` | `amazon.titan-embed-text-v2:0` | Generate embeddings during ingestion |
| `s3vectors:PutVectors`, `GetVectors`, `DeleteVectors`, `QueryVectors`, `ListVectors` | Vector bucket + index ARNs | Store and query embeddings |
| `s3vectors:GetIndex`, `ListIndexes`, `GetVectorBucket` | Vector bucket + index ARNs | KB metadata operations |

### Cognito Identity Pool roles (UI users)

Authenticated users get temporary AWS credentials scoped to their group.

**`redshift-admin` group:**

| Permission | Resource | Why |
|------------|----------|-----|
| `redshift:*`, `redshift-serverless:*`, `redshift-data:*` | `*` | Full modernization workflow |
| `cloudwatch:GetMetricStatistics/ListMetrics/GetMetricData` | `*` | View cluster metrics |
| `dynamodb:PutItem/DeleteItem/GetItem` | Lock table ARN only | Cluster lock operations |
| `bedrock:InvokeAgent` | `*` | Invoke orchestrator from the UI |

**`redshift-viewer` group (read-only):**

| Permission | Resource | Why |
|------------|----------|-----|
| `redshift:Describe*` | `*` | Read cluster configuration |
| `redshift-data:ExecuteStatement/DescribeStatement/GetStatementResult` | `*` | Run assessment queries |
| `cloudwatch:GetMetricStatistics/ListMetrics/GetMetricData` | `*` | View cluster metrics |
| `bedrock:InvokeAgent` | `*` | Invoke orchestrator from the UI |

### CDK bootstrap role (deploy-time only)

The person running `cdk deploy` needs sufficient IAM permissions to create all of the above. At minimum: `iam:CreateRole`, `iam:AttachRolePolicy`, `iam:PutRolePolicy`, `cloudformation:*`, `lambda:*`, `bedrock:*`, `dynamodb:*`, `cognito-idp:*`, `cognito-identity:*`, `s3:*`, `s3vectors:*`. The standard CDK bootstrap (`cdk bootstrap`) sets this up via the `CloudFormationExecutionRole`.

## Quick Start

### Prerequisites

- AWS CLI configured
- Node.js + CDK CLI: `npm install -g aws-cdk`
- Python 3.12+
- [Finch](https://github.com/runfinch/finch) (container runtime used by CDK)
- Bedrock model access enabled for `anthropic.claude-3-5-sonnet-20241022-v2:0` and `amazon.titan-embed-text-v2:0` in your region

### 1. Deploy

```bash
cd src/redshift_agents/cdk
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cdk bootstrap aws://ACCOUNT_ID/REGION
cdk deploy
```

CDK provisions everything and prints outputs. The KB ingestion job runs automatically — no manual sync needed.

### 2. Configure

```bash
cp src/redshift_agents/.env.example src/redshift_agents/.env
# Fill in values from CDK outputs
```

| Variable | Source |
|----------|--------|
| `ORCHESTRATOR_AGENT_ID` | CDK output `OrchestratorAgentId` |
| `ORCHESTRATOR_AGENT_ALIAS_ID` | CDK output `OrchestratorAliasId` |
| `ASSESSMENT_AGENT_ID` | CDK output `AssessmentAgentId` |
| `ARCHITECTURE_AGENT_ID` | CDK output `ArchitectureAgentId` |
| `EXECUTION_AGENT_ID` | CDK output `ExecutionAgentId` |
| `COGNITO_USER_POOL_ID` | CDK output `CognitoUserPoolId` |
| `COGNITO_APP_CLIENT_ID` | CDK output `CognitoAppClientId` |
| `COGNITO_IDENTITY_POOL_ID` | CDK output `CognitoIdentityPoolId` |
| `AWS_REGION` | Your deployment region (default: `us-east-2`) |

### 3. Create a Cognito User

Self-registration is disabled. Create users via the CLI:

```bash
aws cognito-idp admin-create-user \
  --user-pool-id <CognitoUserPoolId> \
  --username your@email.com \
  --temporary-password TempPass123! \
  --user-attributes Name=email,Value=your@email.com

aws cognito-idp admin-add-user-to-group \
  --user-pool-id <CognitoUserPoolId> \
  --username your@email.com \
  --group-name redshift-admin
```

### 4. Run the UI

```bash
pip install -r src/redshift_agents/ui/requirements.txt
cd src/redshift_agents
streamlit run ui/app.py
```

Sign in with your email and temporary password. You'll be prompted to set a new password on first login.

## Using the UI

- Type a message like *"Assess cluster `prod-cluster-01` in `us-east-2`"* to start
- The sidebar shows the active cluster and session info
- Each agent response includes a **🔍 Agent reasoning** expander — click it to see the model's rationale, tool calls, sub-agent delegation, and KB lookups
- Use **🗑️ Forget Cluster Memory** to wipe history for the active cluster and restart assessment fresh
- Use **🔄 New Session** to start a new conversation without clearing memory

## Knowledge Base

The Architecture Agent uses a Bedrock Knowledge Base (S3 Vectors, Titan Embed v2) for Redshift sizing guidance. CDK fully automates this:

1. Uploads docs from `knowledge_base/architecture/` to S3 via `BucketDeployment`
2. Creates `AWS::S3Vectors::VectorBucket` and `AWS::S3Vectors::Index`
3. Creates `AWS::Bedrock::KnowledgeBase` with `S3_VECTORS` storage
4. Triggers `StartIngestionJob` via a CDK custom resource

To add new KB content: drop files into `knowledge_base/architecture/` and run `cdk deploy`.

## Project Structure

```
src/redshift_agents/
├── cdk/                    # CDK stack (one-click deploy)
├── lambdas/                # Lambda action group handlers
├── schemas/                # OpenAPI 3.0 schemas for action groups
├── tools/                  # boto3 tool implementations
├── orchestrator/           # Orchestrator system prompt
├── subagents/              # Sub-agent system prompts
├── knowledge_base/         # Docs indexed into Bedrock KB
├── ui/                     # Streamlit chat UI + Cognito auth
├── tests/                  # 101 tests (unit + 23 property-based)
├── models.py               # Dataclasses
└── .env.example
```

## Running Tests

No AWS credentials needed — all AWS calls are mocked:

```bash
pip install -r src/redshift_agents/tests/requirements-test.txt
pytest src/redshift_agents/tests/ -v
```

## Cost Estimates

All prices are US East (N. Virginia / Ohio) on-demand rates as of March 2026. See [aws.amazon.com/bedrock/pricing](https://aws.amazon.com/bedrock/pricing/) for current rates.

### Model pricing

| Model | Input | Output |
|-------|-------|--------|
| Claude 3.5 Sonnet v2 | $6.00 / 1M tokens | $30.00 / 1M tokens |
| Titan Embed Text v2 (KB ingestion) | $0.02 / 1M tokens | — |

### Per-migration cost estimate

A typical end-to-end migration (assessment → architecture → execution) involves roughly 4–6 agent turns, each triggering 2–4 sub-agent calls. Assuming ~50K input tokens and ~15K output tokens across all 4 agents per migration:

| Item | Estimate |
|------|----------|
| Claude 3.5 Sonnet v2 — input (50K tokens) | ~$0.30 |
| Claude 3.5 Sonnet v2 — output (15K tokens) | ~$0.45 |
| Titan Embed v2 — KB ingestion (one-time, ~20K tokens) | < $0.01 |
| Lambda invocations (assessment + execution tools) | < $0.01 |
| DynamoDB (cluster lock reads/writes) | < $0.01 |
| **Total per migration** | **~$0.75 – $1.50** |

Token usage scales with cluster complexity — a cluster with many WLM queues and a multi-workgroup architecture will use more tokens than a simple 1:1 migration.

### Ongoing infrastructure cost (idle)

These resources persist after deployment and incur charges even when not actively migrating:

| Resource | Monthly cost |
|----------|-------------|
| S3 Vectors storage (~4 KB docs × 1024-dim embeddings, < 1 MB) | < $0.01 |
| S3 bucket (KB source docs, < 1 MB) | < $0.01 |
| DynamoDB (PAY_PER_REQUEST, no idle charge) | $0.00 |
| Lambda (no idle charge) | $0.00 |
| Bedrock Agents (no idle charge) | $0.00 |
| Cognito User Pool (up to 50K MAUs free tier) | $0.00 |
| **Total idle infrastructure** | **~$0.00 – $0.05 / month** |

### Cost optimisation tips

- The foundation model is configurable via CDK context (`foundation_model` in `cdk.json`). Switching to a smaller model (e.g. Claude 3 Haiku at $0.25/$1.25 per 1M tokens) can reduce per-migration cost by ~80% if reasoning quality is sufficient for your clusters.
- KB ingestion only runs on `cdk deploy` — it does not incur recurring embedding costs.
- S3 Vectors query costs scale with index size and query volume; for this KB (< 10K vectors) they are negligible.

> These are estimates only. Actual costs depend on cluster complexity, conversation length, and number of migrations. Always verify current pricing at [aws.amazon.com/bedrock/pricing](https://aws.amazon.com/bedrock/pricing/).

## Teardown

```bash
cd src/redshift_agents/cdk && cdk destroy
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache 2.0 — see [LICENSE](LICENSE).
