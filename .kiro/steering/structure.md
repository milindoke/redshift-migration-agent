# Project Structure

```
src/redshift_agents/
├── cdk/                         # CDK infrastructure (one-click deploy)
│   ├── app.py                   # CDK app entry point
│   ├── stack.py                 # Full stack: Lambda, Bedrock Agents, KB, Cognito, DynamoDB
│   └── cdk.json                 # CDK config (foundation model, Finch container runtime)
├── lambdas/                     # Lambda action group handlers
│   ├── assessment_handler.py    # listRedshiftClusters, analyzeRedshiftCluster, getClusterMetrics, getWlmConfiguration
│   ├── execution_handler.py     # createClusterSnapshot, executeRedshiftQuery, createServerlessNamespace, createServerlessWorkgroup, restoreSnapshotToServerless, setupDataSharing
│   └── cluster_lock_handler.py  # acquireClusterLock, releaseClusterLock
├── schemas/                     # OpenAPI 3.0 schemas for Bedrock Agent action groups
├── tools/                       # Tool implementations (plain Python, boto3 calls)
│   ├── redshift_tools.py        # 10 Redshift/Serverless/CloudWatch tools
│   ├── cluster_lock.py          # DynamoDB cluster locking
│   └── audit_logger.py          # Structured JSON audit logging
├── orchestrator/                # Orchestrator system prompt constant
├── subagents/                   # Sub-agent system prompt constants
├── knowledge_base/              # Reference docs uploaded to S3 and indexed into Bedrock KB
│   ├── architecture/            # Docs for Architecture Agent KB (RPU sizing, migration patterns, data sharing)
│   ├── assessment/              # Docs for reference (embedded in assessment agent prompt)
│   └── execution/               # Docs for reference (embedded in execution agent prompt)
├── ui/                          # Streamlit chat UI with Cognito auth
│   ├── app.py                   # Main UI (sign-in, chat, agent trace, cluster memory, forget memory)
│   └── auth.py                  # Cognito auth utilities (JWT decode, email display, Identity Pool)
├── tests/                       # 101 tests (unit + 23 property-based)
├── models.py                    # Dataclasses (Assessment/Architecture/Execution results, locks, audit)
├── deploy.sh                    # Deploy script (runs cdk deploy)
├── requirements.txt
└── .env.example
```

## Architecture Patterns

- **Agent pattern**: Each agent is a Bedrock Agent (CfnAgent) with a system prompt constant in its Python module.
- **Knowledge Base pattern**: The Architecture Agent has a Bedrock Knowledge Base (S3 Vectors storage) attached at deploy time. CDK provisions the S3 Vector Bucket, Vector Index, KB, data source, and triggers `StartIngestionJob` via a custom resource — fully automated, no manual sync needed. Docs live in `knowledge_base/architecture/` and are uploaded to S3 by `BucketDeployment` on every `cdk deploy`.
- **Tool pattern**: Tools in `tools/redshift_tools.py` are plain Python functions that call AWS APIs via boto3 and return dicts. Errors return `{"error": ...}`, never raise. Lambda handlers dispatch to these functions based on `apiPath`.
- **Region resolution**: All tools use `_resolve_region()` — checks parameter first, then `AWS_REGION` env var, then falls back to `us-east-2`. No hardcoded regions.
- **Orchestrator** is a Bedrock Supervisor Agent that delegates to sub-agents via `AssociateAgentCollaborator`. It has `listRedshiftClusters` and cluster lock as direct action groups.
- **Memory**: All agents use `SESSION_SUMMARY` memory (30-day retention) with `cluster_id` as `memoryId` so conversation history persists per cluster across users and sessions.
- **Agent trace**: `invoke_agent` is called with `enableTrace=True`. The UI parses `orchestrationTrace` events (rationale, invocationInput, observation) and renders them in a collapsible expander per response.
- **User display**: `auth.py` `extract_user_id_from_payload` prefers `email` → `preferred_username` → `cognito:username` → `sub` so the UI shows a human-readable name instead of the Cognito UUID.

## Conventions
- System prompts are module-level constants named `*_SYSTEM_PROMPT`.
- Every tool accepts `region` and `user_id` for cross-region support and identity propagation.
- Every tool emits audit events via `emit_audit_event(initiated_by=user_id)`.
- Environment config via `.env` files (see `.env.example`).
- CDK manages all infrastructure — no manual AWS console setup needed.
- To add new KB docs for the Architecture Agent: drop files into `knowledge_base/architecture/` and run `cdk deploy`. The ingestion job re-runs automatically.
