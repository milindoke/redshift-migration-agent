# Tech Stack & Build

## Language & Runtime
- Python 3.12+

## Frameworks & SDKs
- **AWS Transform (ATX) BaseAgent SDK** — Agent framework (`eg_platform_base_agent`). Installed from local `.whl` files in `sdk/`.
  - `AsyncBaseOrchestrator` for the orchestrator
  - `AsyncBaseSubagent` for subagents
  - `AgentRuntimeServer` for serving agents over HTTP
- **Strands** — Tool definitions use `@tool` decorator from `strands.tools`
- **ATX MCP** — Model Context Protocol for inter-agent communication (`mcp.MCPClient`)
- **boto3 / botocore** — AWS SDK for Redshift and CloudWatch API calls

## Key Dependencies
- `aiohttp` — Async HTTP
- `python-dotenv` — Environment config
- `python-json-logger` — Structured logging

## Containerization
- One Dockerfile per agent in `src/redshift_agents/docker/`
- Base image: `python:3.12-slim`
- Docker Compose for local multi-agent testing
- Production target: Amazon Bedrock AgentCore
- Build tool: Finch (or Docker)

## Common Commands

```bash
# Run unit tests (from src/redshift_agents)
pytest tests/ -v

# Build all Docker images
cd src/redshift_agents && ./build-images.sh

# Full deploy workflow (build, push ECR, etc.)
cd src/redshift_agents && ./deploy-with-finch.sh

# Local multi-agent testing
cd src/redshift_agents/docker && docker-compose up

# Install test dependencies
pip install -r src/redshift_agents/tests/requirements-test.txt
```

## Testing
- Framework: `pytest` with `pytest-cov` and `pytest-mock`
- Tests mock all AWS calls via `unittest.mock.patch` on `boto3.client` — no AWS credentials needed locally.
- Test deps are in `src/redshift_agents/tests/requirements-test.txt`.
