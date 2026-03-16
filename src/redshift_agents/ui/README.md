# Redshift Modernization Chat UI

Streamlit-based chat interface with Cognito authentication.

## Prerequisites

- Stack deployed via `cdk deploy`
- Cognito user created and added to `redshift-admin` group
- `.env` file configured with CDK output values

## Run

```bash
cd src/redshift_agents
streamlit run ui/app.py
```

Opens at `http://localhost:8501`.

## Configuration

Set in `.env` (loaded automatically):

| Variable | Description |
|----------|-------------|
| `ORCHESTRATOR_AGENT_ID` | From CDK output |
| `ORCHESTRATOR_AGENT_ALIAS_ID` | From CDK output |
| `COGNITO_USER_POOL_ID` | From CDK output |
| `COGNITO_APP_CLIENT_ID` | From CDK output |
| `COGNITO_IDENTITY_POOL_ID` | From CDK output |
| `AWS_REGION` | Deployment region (default: us-east-2) |

## Usage

1. Sign in with your Cognito credentials
2. Type your modernization request (e.g., "List clusters" or "Modernize cluster my-cluster")
3. The orchestrator guides you through assessment → architecture → execution with approval gates
4. Conversation history persists per cluster — come back later and pick up where you left off
