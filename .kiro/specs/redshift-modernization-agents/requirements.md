# Requirements: Redshift Modernization Agents

## Overview
Build an AI-powered multi-agent system that guides customers through migrating AWS Redshift Provisioned clusters to Serverless, using Strands and Amazon Bedrock AgentCore. The system supports two modernization scenarios: (1) splitting a single Provisioned cluster into multiple Serverless workgroups based on WLM queue analysis, or (2) a straight 1:1 migration from a single Provisioned cluster to a single Serverless workgroup when the cluster is already purpose-built and splitting is not warranted.

## Functional Requirements

### FR-1: Multi-Agent Orchestration
- FR-1.1: An orchestrator agent coordinates the end-to-end modernization workflow
- FR-1.2: The orchestrator delegates all cluster operations to specialized subagents
- FR-1.3: The orchestrator resides in the customer account alongside subagents
- FR-1.4: The orchestrator maintains conversation state and context across interactions
- FR-1.5: Three subagents handle domain-specific tasks: assessment, architecture, execution

### FR-2: Assessment Agent
- FR-2.1: List all Redshift Provisioned clusters in the customer account + region; if a specific cluster is not provided, present the list and let the user select one
- FR-2.2: For the selected cluster, retrieve configuration details (node type, count, status, version, encryption, VPC, public access, enhanced VPC routing)
- FR-2.3: Retrieve CloudWatch performance metrics (CPU, connections, network, disk, latency)
- FR-2.4: Query the cluster's WLM configuration to determine the number and nature of WLM queues
- FR-2.5: For each WLM queue, gather: number of queries waiting, total wait time vs execution time, number of queries spilling to disk, and amount of disk spill
- FR-2.6: Present the WLM analysis in a way that clearly highlights contention problems — long wait times, disk spill, queue saturation — to build the case for why a multi-warehouse architecture is needed
- FR-2.7: Produce structured JSON output with cluster summary, WLM queue analysis (per-queue metrics), and a narrative summary of identified problems

### FR-3: Architecture Agent
- FR-3.1: Using the assessment results, propose a workgroup split: if multiple WLM queues exist, map each queue to its own Serverless workgroup; if only one queue, interact with the user to split into at minimum a producer workgroup (ETL/write-heavy) and a consumer workgroup (read-heavy/analytics)
- FR-3.2: If the cluster is already purpose-built (e.g., a dedicated consumer or ETL cluster) and splitting is not warranted, propose a 1:1 migration to a single Serverless workgroup — no multi-warehouse split required
- FR-3.3: Run additional diagnostic SQL queries against the cluster to determine a good starting RPU value for each proposed workgroup
- FR-3.4: Recommend AI-driven scaling with price-performance targets for each workgroup; minimum RPU recommendation must be 32 RPU (required for AI-driven scaling)
- FR-3.5: Support three architecture patterns for multi-workgroup scenarios: hub-and-spoke with data sharing, independent warehouses, hybrid
- FR-3.6: Include cost estimates and migration complexity assessment
- FR-3.7: Produce structured JSON output with workgroup specs (name, RPU range, scaling policy), data flow, and trade-offs

### FR-4: Execution Agent
- FR-4.1: Create the Serverless namespace and workgroups with the RPU settings recommended by the architecture agent
- FR-4.2: Restore a snapshot of the Provisioned cluster into the new Serverless namespace
- FR-4.3: Set up data sharing between workgroups if hub-and-spoke architecture is selected
- FR-4.4: Generate a plan for migrating users and applications from old WLM queues to the corresponding new workgroups
- FR-4.5: Validate query performance on the new workgroups before cutover (run representative queries, compare latency/throughput)
- FR-4.6: Define rollback procedures at each step in case of issues
- FR-4.7: Plan for minimal/zero downtime cutover from Provisioned to Serverless

### FR-5: Shared Agent Capabilities
- FR-5.1: All agents can discover Redshift Provisioned clusters in the customer account via the Redshift API
- FR-5.2: All agents can retrieve CloudWatch metrics for any cluster
- FR-5.3: All agents can execute read-only SQL queries against Redshift system tables via the Redshift Data API, with the initiator's identity passed as `DbUser` for full audit traceability
- FR-5.4: All tool invocations and agent actions are logged with structured audit events including `customer_account_id`, `initiated_by`, `agent_name`, `cluster_id`, and timestamp
- FR-5.5: The orchestrator logs every subagent delegation (which subagent, what input, what result) for full workflow traceability

### FR-6: Workflow Phases
- FR-6.1: Phase 1 — Discovery & Assessment: collect cluster ID/region, invoke assessment agent, analyze WLM queues, surface contention problems
- FR-6.2: Gate 1 — Present assessment results to the user; require explicit approval before proceeding to architecture design
- FR-6.3: Phase 2 — Architecture Design: invoke architecture agent with assessment results, propose workgroup split with RPU sizing
- FR-6.4: Gate 2 — Present proposed architecture to the user; require explicit approval before proceeding to execution
- FR-6.5: Phase 3 — Migration Execution: invoke execution agent to create namespace/workgroups, restore snapshot, migrate users, validate, cutover
- FR-6.6: The orchestrator must not advance to the next phase without user confirmation at each gate

## Non-Functional Requirements

### NFR-1: Single-Account Security
- NFR-1.1: All agents (orchestrator + subagents) run within the customer account
- NFR-1.2: Customer data never leaves the customer account
- NFR-1.3: No service account or cross-account dependency
- NFR-1.4: Each agent has its own IAM role scoped to least-privilege for that agent's specific needs (e.g., assessment = read-only Redshift + CloudWatch; execution = Redshift write + Serverless create)

### NFR-2: Session Isolation & Cluster Locking
- NFR-2.1: Each agent invocation gets its own session, managed by Bedrock AgentCore; concurrent users in the same account have fully isolated conversations
- NFR-2.2: Two users in the same account cannot work on the same Redshift cluster simultaneously; the orchestrator must acquire a cluster-level lock before starting a workflow and release it on completion or failure
- NFR-2.3: If a cluster is already being worked on, the orchestrator must inform the user who holds the lock and when it was acquired

### NFR-3: Deployment
- NFR-3.1: Agents deployed to Amazon Bedrock AgentCore via `agentcore launch` (direct code deploy, no Docker required)
- NFR-3.2: Deployment region is the customer's choice
- NFR-3.3: Agents can analyze and migrate Redshift clusters in any region; the target cluster region is a parameter, not tied to the agent's deployment region

### NFR-4: Testing
- NFR-4.1: Unit tests mock all AWS API calls via `unittest.mock.patch` on `boto3.client`
- NFR-4.2: No AWS credentials required for local testing
- NFR-4.3: Tests run with `pytest tests/ -v`

### NFR-5: Observability
- NFR-5.1: All agents emit structured JSON logs to CloudWatch Logs

### NFR-6: Fleet Audit Observability (Redshift Service Team)
- NFR-6.1: All agent lifecycle events and tool invocations emit structured JSON audit logs to a dedicated `redshift_modernization_audit` logger
- NFR-6.2: Every audit event includes `customer_account_id`, `agent_name`, `event_type`, `cluster_id`, `region`, and ISO 8601 `timestamp`
- NFR-6.3: During deployment/setup, the customer is prompted to opt-in to CloudWatch cross-account log sharing with the Redshift Service Team; the prompt explains that opting in allows AWS Support to better assist with the modernization project
- NFR-6.4: If the customer opts in, audit logs are shared to a central Redshift Service Team log destination via CloudWatch cross-account subscription
- NFR-6.5: CloudTrail automatically captures underlying Redshift/CloudWatch API calls with caller account context (available to the Service Team regardless of opt-in)
- NFR-6.6: Audit events cover: `agent_start`, `tool_invocation`, `workflow_start`, `workflow_complete`, `phase_start`, `phase_complete`, `error`

### NFR-7: End-to-End Identity Propagation & Audit Traceability (Customer)
- NFR-7.1: The identity of the person who initiated a request must be propagated through every layer: orchestrator → subagent → Redshift Data API
- NFR-7.2: Every audit log event must include a `user_id` or `initiated_by` field identifying the individual who triggered the workflow
- NFR-7.3: SQL queries executed against Redshift via the Data API must pass the initiator's identity as the `DbUser` parameter so Redshift audit logs (`STL_CONNECTION_LOG`, `STL_USERLOG`) attribute queries to the individual, not just the IAM role
- NFR-7.4: CloudTrail must capture the initiator's identity via IAM session tags (e.g., `PrincipalTag/user`) on every API call made by the agent
- NFR-7.5: The full audit chain must be reconstructable: person → agent session → tool invocations → SQL executions → Redshift audit logs → CloudTrail events
- NFR-7.6: Customers can audit exactly who triggered what action, when, and against which cluster — this is a non-negotiable security requirement
