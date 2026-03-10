# Requirements: Redshift Modernization Agents

## Overview
Build an AI-powered multi-agent system that guides customers through migrating AWS Redshift Provisioned clusters to Serverless, using the AWS Transform (ATX) BaseAgent SDK and Amazon Bedrock AgentCore.

## Functional Requirements

### FR-1: Multi-Agent Orchestration
- FR-1.1: An orchestrator agent coordinates the end-to-end modernization workflow
- FR-1.2: The orchestrator delegates all cluster operations to specialized subagents via MCP `InvokeAgent`
- FR-1.3: The orchestrator resides in the customer account alongside subagents
- FR-1.4: The orchestrator maintains conversation state and context across interactions
- FR-1.5: Four subagents handle domain-specific tasks: assessment, scoring, architecture, execution

### FR-2: Assessment Agent
- FR-2.1: Analyze Redshift cluster configuration (node type, count, status, version)
- FR-2.2: Extract security settings (encryption, VPC, public access, enhanced VPC routing)
- FR-2.3: Retrieve CloudWatch performance metrics (CPU, connections, network, disk, latency)
- FR-2.4: List all clusters in a given region when cluster ID is not specified
- FR-2.5: Identify usage patterns (workload type, peak hours, access patterns)
- FR-2.6: Produce structured JSON output with findings, risk assessment, and recommendations

### FR-3: Scoring Agent
- FR-3.1: Evaluate clusters against best practices across three weighted categories
- FR-3.2: Security scoring (35% weight): encryption, network security, VPC routing, access controls, audit logging — 35 points possible
- FR-3.3: Performance scoring (35% weight): node type, cluster sizing, disk management, query performance, WLM — 35 points possible
- FR-3.4: Cost optimization scoring (30% weight): reserved instances, right-sizing, snapshots, pause/resume — 30 points possible
- FR-3.5: Produce overall 0–100 score with A–F grade (A=90+, B=80–89, C=70–79, D=60–69, F=<60)
- FR-3.6: Generate prioritized recommendations with estimated point impact and effort

### FR-4: Architecture Agent
- FR-4.1: Design multi-warehouse topology based on workload analysis
- FR-4.2: Support three architecture patterns: hub-and-spoke, independent warehouses, hybrid
- FR-4.3: Recommend workload separation strategies (ETL, analytics, reporting, ML, ad-hoc)
- FR-4.4: Provide sizing recommendations per warehouse (node types, WLM, concurrency scaling)
- FR-4.5: Include cost estimates and migration complexity assessment
- FR-4.6: Produce structured JSON output with warehouse specs, data flow, and trade-offs

### FR-5: Execution Agent
- FR-5.1: Create phased migration plans (5 phases: preparation, data migration, pilot, incremental, cutover)
- FR-5.2: Define validation criteria and rollback procedures per phase
- FR-5.3: Generate infrastructure-as-code templates (CloudFormation/CDK)
- FR-5.4: Plan for minimal/zero downtime migration
- FR-5.5: Include monitoring plan with metrics, alert thresholds, and dashboards
- FR-5.6: Estimate realistic timelines (12–18 weeks for full modernization)

### FR-6: Shared Redshift Tools
- FR-6.1: `analyze_redshift_cluster(cluster_id, region)` — calls Redshift `DescribeClusters` API
- FR-6.2: `get_cluster_metrics(cluster_id, region, hours)` — fetches 7 CloudWatch metrics with summary statistics
- FR-6.3: `list_redshift_clusters(region)` — lists all clusters with basic info
- FR-6.4: All tools return structured dicts; errors return `{"error": ..., "cluster_id": ..., "region": ...}`

### FR-7: Workflow Phases
- FR-7.1: Phase 1 — Discovery & Assessment: collect cluster ID/region, invoke assessment agent
- FR-7.2: Phase 2 — Best Practices Evaluation: invoke scoring agent with assessment results
- FR-7.3: Phase 3 — Architecture Design: invoke architecture agent with requirements
- FR-7.4: Phase 4 — Modernization Execution: invoke execution agent for phased implementation

## Non-Functional Requirements

### NFR-1: Single-Account Security
- NFR-1.1: All agents (orchestrator + subagents) run within the customer account
- NFR-1.2: Customer data never leaves the customer account
- NFR-1.3: No service account or cross-account dependency
- NFR-1.4: All subagent invocations include `customer_account_id` for namespace isolation
- NFR-1.5: Single IAM role set with least-privilege permissions for all agents

### NFR-2: Conversation Isolation
- NFR-2.1: Namespace-based session management keyed by `customer_account_id`
- NFR-2.2: Session ID format: `{namespace}:{conversation_id}`
- NFR-2.3: Isolated conversation history per customer

### NFR-3: Deployment
- NFR-3.1: Each agent packaged as a Docker container (python:3.12-slim base)
- NFR-3.2: Deployed to Amazon Bedrock AgentCore
- NFR-3.3: All images pushed to customer account ECR
- NFR-3.4: Health check endpoint at `/ping` on each agent
- NFR-3.5: Default region: us-east-2

### NFR-4: Testing
- NFR-4.1: Unit tests mock all AWS API calls via `unittest.mock.patch` on `boto3.client`
- NFR-4.2: No AWS credentials required for local testing
- NFR-4.3: Tests run with `pytest tests/ -v`

### NFR-5: Observability
- NFR-5.1: Structured JSON logging via `python-json-logger`
- NFR-5.2: CloudWatch dashboards and alarms for each agent
- NFR-5.3: SNS notifications for error conditions

### NFR-6: Fleet Audit Observability
- NFR-6.1: All agent lifecycle events and tool invocations emit structured JSON audit logs to a dedicated `redshift_modernization_audit` logger
- NFR-6.2: Every audit event includes `customer_account_id`, `agent_name`, `event_type`, `cluster_id`, `region`, and ISO 8601 `timestamp`
- NFR-6.3: The Redshift Service Team can query fleet-wide usage via CloudWatch Logs Insights across customer accounts
- NFR-6.4: CloudTrail automatically captures underlying Redshift/CloudWatch API calls with caller account context
- NFR-6.5: Audit events cover: `agent_start`, `tool_invocation`, `workflow_start`, `workflow_complete`, `phase_start`, `phase_complete`, `scoring_result`, `error`
