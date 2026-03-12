# Redshift Modernization Chat UI

Streamlit-based chat interface for the Redshift Modernization orchestrator agent.

## Prerequisites

- Agents deployed to Bedrock AgentCore (`./deploy-agentcore.sh`)
- AWS credentials configured with `bedrock-agent-runtime:InvokeAgent` permission
- Python 3.12+

## Setup

```bash
pip install -r ui/requirements.txt
```

## Run

```bash
cd src/redshift_agents
streamlit run ui/app.py
```

The app opens at `http://localhost:8501`.

## Configuration

Set these environment variables before running:

| Variable | Default | Description |
|----------|---------|-------------|
| `ORCHESTRATOR_AGENT_ID` | `redshift-orchestrator` | Bedrock AgentCore agent ID |
| `ORCHESTRATOR_AGENT_ALIAS_ID` | `TSTALIASID` | Agent alias ID |
| `AWS_REGION` | `us-east-2` | AWS region |

Example:
```bash
export ORCHESTRATOR_AGENT_ID=ABCDEF1234
export ORCHESTRATOR_AGENT_ALIAS_ID=TSTALIASID
export AWS_REGION=us-east-2
streamlit run ui/app.py
```

## Usage

1. Enter your User ID in the sidebar (required for audit traceability)
2. Type your modernization request in the chat input
3. The orchestrator guides you through 3 phases with approval gates:
   - Assessment → approve → Architecture → approve → Execution
4. Click "New Session" in the sidebar to start over
