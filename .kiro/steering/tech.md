# Tech Stack & Build

## Language & Runtime
- Python 3.12+

## Frameworks & SDKs
- **Amazon Bedrock Agents** — Fully managed agents with action groups, multi-agent collaboration (supervisor/collaborator), and session memory.
- **AWS CDK** — Infrastructure-as-code for one-click deployment (`cdk deploy`).
- **boto3 / botocore** — AWS SDK for Redshift, Redshift Serverless, Redshift Data API, CloudWatch, DynamoDB, Cognito, and Bedrock Agent Runtime.
- **Streamlit** — Chat UI with Cognito authentication, agent reasoning trace, and cluster memory management.

## Key Dependencies
- `python-json-logger` — Structured JSON logging for audit events
- `python-dotenv` — Environment config
- `aws-cdk-lib` — CDK infrastructure (includes `aws_s3vectors`, `aws_s3_deployment`, `custom_resources`)
- `hypothesis` — Property-based testing (test dependency)

## Region Configuration
- All tools resolve region from `AWS_REGION` environment variable (default: `us-east-2`)
- No hardcoded regions anywhere in the codebase
- Tools use `_resolve_region()` helper: parameter → env var → fallback

## Deployment
- Single `cdk deploy` provisions everything: Lambda functions, Bedrock Agents, Knowledge Base (S3 Vectors), DynamoDB, Cognito, IAM roles
- CDK stack: `src/redshift_agents/cdk/stack.py`
- Foundation model configurable via CDK context in `cdk.json`
- Container runtime: Finch (configured in `cdk.json` via `containerizationOptions`)
- KB ingestion is triggered automatically post-deploy via a CDK custom resource (`StartIngestionJob`)

## Common Commands

```bash
# Deploy all infrastructure
cd src/redshift_agents/cdk && cdk deploy

# Run unit tests (no AWS credentials needed)
pytest src/redshift_agents/tests/ -v

# Run the Streamlit UI
cd src/redshift_agents && streamlit run ui/app.py

# Tear down
cd src/redshift_agents/cdk && cdk destroy
```

## Testing
- Framework: `pytest` with `pytest-cov`, `pytest-mock`, and `hypothesis`
- 101 tests across 8 test files (unit + 23 property-based via hypothesis)
- Tests mock all AWS calls via `unittest.mock.patch` on `boto3.client` — no AWS credentials needed locally
- Property tests use `@settings(max_examples=100)` and validate 23 correctness properties
- Test deps: `src/redshift_agents/tests/requirements-test.txt`
