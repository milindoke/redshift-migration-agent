# Redshift Modernization Agents

AI-powered multi-agent system for migrating Amazon Redshift Provisioned clusters to Serverless, built on fully managed Amazon Bedrock Agents.

## What This Does

- **3-phase workflow**: Assessment → Architecture → Execution with human approval gates
- **WLM queue analysis**: Surfaces contention problems (wait times, disk spill, saturation)
- **Workgroup design**: Maps WLM queues to Serverless workgroups with RPU sizing
- **Automated execution**: Creates namespaces/workgroups, snapshots, restores, data sharing, validation
- **Two migration paths**: Multi-workgroup split or 1:1 migration
- **Cognito authentication**: JWT-based identity, no manual user ID entry
- **Cluster-level memory**: Agents remember previous conversations per cluster

## Architecture

- **Orchestrator** (Supervisor Agent) — coordinates workflow, approval gates, cluster locks, lists clusters directly
- **Assessment Agent** — cluster config analysis, CloudWatch metrics, WLM queue contention
- **Architecture Agent** — workgroup design, RPU sizing, migration pattern selection
- **Execution Agent** — create resources, snapshot/restore, data sharing, validation

All infrastructure provisioned via AWS CDK. Single `cdk deploy` — no manual setup.

## Region Configuration

All tools resolve region from the `AWS_REGION` environment variable (default: `us-east-2`). No hardcoded regions. Users can request a different region in conversation and the agent remembers it for the session.

## Quick Start

### Prerequisites
- AWS CLI configured with credentials
- Node.js (for CDK CLI)
- Python 3.12+
- CDK CLI: `npm install -g aws-cdk`

### 1. Deploy

```bash
cd src/redshift_agents/cdk
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cdk bootstrap aws://ACCOUNT_ID/REGION
cdk deploy
```

### 2. Configure

Copy CDK outputs into your `.env` file:

```bash
cp .env.example .env
# Edit .env with values from CDK outputs
```

### 3. Create a Cognito User

```bash
aws cognito-idp admin-create-user \
  --user-pool-id <CognitoUserPoolId> \
  --username your-email@example.com \
  --temporary-password TempPass123! \
  --user-attributes Name=email,Value=your-email@example.com

aws cognito-idp admin-add-user-to-group \
  --user-pool-id <CognitoUserPoolId> \
  --username your-email@example.com \
  --group-name redshift-admin
```

### 4. Run the UI

```bash
pip install -r ui/requirements.txt
cd src/redshift_agents
streamlit run ui/app.py
```

### Run Tests

```bash
pip install -r tests/requirements-test.txt
pytest tests/ -v
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `us-east-2` | Deployment region (tools auto-resolve from this) |
| `ORCHESTRATOR_AGENT_ID` | — | From CDK output |
| `ORCHESTRATOR_AGENT_ALIAS_ID` | — | From CDK output |
| `COGNITO_USER_POOL_ID` | — | From CDK output |
| `COGNITO_APP_CLIENT_ID` | — | From CDK output |
| `COGNITO_IDENTITY_POOL_ID` | — | From CDK output |
| `DYNAMODB_LOCK_TABLE` | `redshift_modernization_locks` | Lock table name |

## Project Structure

```
src/redshift_agents/
├── cdk/                         # CDK infrastructure (one-click deploy)
│   ├── app.py                   # CDK app entry point
│   ├── stack.py                 # Full stack: Lambda, Bedrock Agents, Cognito, DynamoDB
│   └── cdk.json                 # CDK config (foundation model selection)
├── lambdas/                     # Lambda action group handlers
│   ├── assessment_handler.py    # 4 assessment tools
│   ├── execution_handler.py     # 6 execution tools
│   └── cluster_lock_handler.py  # 2 lock tools
├── schemas/                     # OpenAPI 3.0 schemas for action groups
├── tools/                       # Tool implementations (boto3 calls)
│   ├── redshift_tools.py        # 10 Redshift/Serverless/CloudWatch tools
│   ├── cluster_lock.py          # DynamoDB cluster locking
│   └── audit_logger.py          # Structured JSON audit logging
├── orchestrator/                # Orchestrator system prompt
├── subagents/                   # Sub-agent system prompts (with embedded KB)
├── knowledge_base/              # Reference docs (embedded in agent prompts)
├── ui/                          # Streamlit chat UI with Cognito auth
├── tests/                       # 101 tests (unit + 23 property-based)
├── models.py                    # Dataclasses
└── .env.example                 # Environment template
```

## Teardown

```bash
cd src/redshift_agents/cdk
cdk destroy
```
