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

## Teardown

```bash
cd src/redshift_agents/cdk && cdk destroy
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache 2.0 — see [LICENSE](LICENSE).
