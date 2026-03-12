# Tech Stack & Build

## Language & Runtime
- Python 3.12+

## Frameworks & SDKs
- **Strands Agent** — Agent framework (`strands.Agent`). Tools use `@tool` decorator from `strands.tools`.
- **Amazon Bedrock AgentCore** — Deployment runtime (`bedrock_agentcore.runtime.BedrockAgentCoreApp`). Agents deployed via `agentcore launch`.
- **boto3 / botocore** — AWS SDK for Redshift, Redshift Serverless, Redshift Data API, CloudWatch, DynamoDB, and Bedrock Agent Runtime calls.

## Key Dependencies
- `python-json-logger` — Structured JSON logging for audit events
- `python-dotenv` — Environment config
- `hypothesis` — Property-based testing (test dependency)

## Deployment
- Direct code deploy via `agentcore launch` (no Docker/containers)
- One `agentcore launch` command per agent (orchestrator + 3 subagents)
- Deploy script: `src/redshift_agents/deploy-agentcore.sh`
- Per-agent IAM policies in `src/redshift_agents/iam/`

## Common Commands

```bash
# Run unit tests (from src/redshift_agents)
pytest tests/ -v

# Deploy all agents to Bedrock AgentCore
cd src/redshift_agents && ./deploy-agentcore.sh

# Install test dependencies
pip install -r src/redshift_agents/tests/requirements-test.txt
```

## Testing
- Framework: `pytest` with `pytest-cov`, `pytest-mock`, and `hypothesis`
- 68 tests across 7 test files (30 unit + 19 property-based via hypothesis)
- Tests mock all AWS calls via `unittest.mock.patch` on `boto3.client` — no AWS credentials needed locally.
- `conftest.py` stubs `strands` and `bedrock_agentcore` modules for the test environment.
- Property tests use `@settings(max_examples=100)` and validate 19 correctness properties.
- Test deps are in `src/redshift_agents/tests/requirements-test.txt`.
