# Project Structure

```
src/redshift_agents/
├── cdk/                         # CDK infrastructure (one-click deploy)
│   ├── app.py                   # CDK app entry point
│   ├── stack.py                 # Full stack: Lambda, Bedrock Agents, Cognito, DynamoDB
│   └── cdk.json                 # CDK config (foundation model selection)
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
├── subagents/                   # Sub-agent system prompt constants (with embedded KB content)
├── knowledge_base/              # Reference docs (embedded in agent prompts, kept for documentation)
├── ui/                          # Streamlit chat UI with Cognito auth
│   ├── app.py                   # Main UI (sign-in, chat, cluster memory)
│   └── auth.py                  # Cognito auth utilities (JWT, Identity Pool)
├── tests/                       # 101 tests (unit + 23 property-based)
├── models.py                    # Dataclasses (Assessment/Architecture/Execution results, locks, audit)
├── deploy-agentcore.sh          # Deploy script (runs cdk deploy)
├── requirements.txt
└── .env.example
```

## Architecture Patterns

- **Agent pattern**: Each agent is a Bedrock Agent (CfnAgent) with a system prompt constant in its Python module. System prompts include embedded knowledge base content.
- **Tool pattern**: Tools in `tools/redshift_tools.py` are plain Python functions that call AWS APIs via boto3 and return dicts. Errors return `{"error": ...}`, never raise. Lambda handlers dispatch to these functions based on `apiPath`.
- **Region resolution**: All tools use `_resolve_region()` — checks parameter first, then `AWS_REGION` env var, then falls back to `us-east-2`. No hardcoded regions.
- **Orchestrator** is a Bedrock Supervisor Agent that delegates to sub-agents via `AssociateAgentCollaborator`. It has `listRedshiftClusters` and cluster lock as direct action groups.
- **Memory**: All agents use `SESSION_SUMMARY` memory (30-day retention) with `cluster_id` as `memoryId` so conversation history persists per cluster across users and sessions.

## Conventions
- System prompts are module-level constants named `*_SYSTEM_PROMPT`.
- Every tool accepts `region` and `user_id` for cross-region support and identity propagation.
- Every tool emits audit events via `emit_audit_event(initiated_by=user_id)`.
- Environment config via `.env` files (see `.env.example`).
- CDK manages all infrastructure — no manual AWS console setup needed.
