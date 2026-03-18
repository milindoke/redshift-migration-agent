# Product Overview

Redshift Modernization Agents is an AI-powered multi-agent system that helps customers migrate AWS Redshift Provisioned clusters to Serverless.

## What It Does

The system walks customers through a 3-phase modernization workflow with human-in-the-loop approval gates:
1. **Assessment** — Analyzes cluster configuration, CloudWatch metrics, and WLM queue contention (wait times, disk spill, saturation)
2. **Architecture Design** — Designs Serverless workgroup topology: WLM-to-workgroup mapping, RPU sizing (min 32), three patterns (hub-and-spoke, independent, hybrid), cost estimates
3. **Execution** — Creates namespace/workgroups, restores snapshots, sets up data sharing, migrates users, validates performance, defines rollback procedures, plans cutover

Two migration paths are supported:
- **Multi-workgroup split** — when WLM contention justifies separating workloads into multiple Serverless workgroups
- **1:1 migration** — when the cluster is purpose-built and a single Serverless workgroup suffices

## Key Constraints

- Single-account deployment: all agents (orchestrator + 3 subagents) run within the customer account.
- No service account or cross-account dependency.
- Customer data never leaves the customer account.
- Cluster-level locking via DynamoDB prevents concurrent operations on the same cluster.
- End-to-end identity propagation: user_id flows from orchestrator → subagent → tool → Redshift Data API → CloudTrail.
- Approval gates between phases: orchestrator will not advance without explicit user approval.
- Default AWS region is configured via `AWS_REGION` environment variable (default: `us-east-2`). No hardcoded regions in code. Users can switch regions in conversation and the agent remembers the selection.
- Cluster-level memory: agents remember previous conversations per cluster (30-day retention). Any user working on the same cluster sees the shared history.
- UI displays the user's email (from JWT `email` claim) rather than the Cognito `sub` UUID.
- Agent reasoning trace is visible in the UI: every response includes a collapsible expander showing rationale, tool calls, sub-agent delegation, and KB lookups (`enableTrace=True`).
