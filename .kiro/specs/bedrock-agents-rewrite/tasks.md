# Implementation Plan: Bedrock Agents Rewrite

## Overview

Rewrite the Redshift Modernization Agents system from Strands Agents + Bedrock AgentCore to fully managed Amazon Bedrock Agents. The implementation proceeds bottom-up: shared modules first, then Lambda handlers, OpenAPI schemas, CDK infrastructure, Cognito auth, Streamlit UI changes, and finally tests. Each task builds on the previous so there is no orphaned code.

## Tasks

- [x] 1. Extract tool logic into plain Python functions and update shared modules
  - [x] 1.1 Refactor `src/redshift_agents/tools/redshift_tools.py` — remove `@tool` decorators and Strands imports, convert all 9 tool functions to plain Python functions with identical signatures, boto3 calls, error handling (`{"error": ...}` dicts), and parameter defaults
    - Keep `region` defaulting to `"us-east-1"`, keep `user_id` parameter on every function
    - Preserve `emit_audit_event(initiated_by=user_id)` calls in every function
    - Preserve `DbUser=user_id` in all `execute_statement` calls
    - _Requirements: 1.2, 1.3, 1.5, 13.2, 13.5_

  - [x] 1.2 Refactor `src/redshift_agents/tools/audit_logger.py` — remove any Strands/AgentCore imports, ensure `emit_audit_event` is a standalone function that logs structured JSON to the `redshift_modernization_audit` logger with all required fields (`timestamp`, `event_type`, `agent_name`, `customer_account_id`, `initiated_by`, `cluster_id`, `region`, `details`)
    - _Requirements: 6.1, 6.4, 6.5, 14.1, 14.2, 14.5_

  - [x] 1.3 Refactor `src/redshift_agents/tools/cluster_lock.py` — remove any Strands/AgentCore imports, ensure `acquire_lock` and `release_lock` are plain functions using DynamoDB conditional writes (`attribute_not_exists(cluster_id)`) with 24-hour TTL
    - On acquisition failure, return `{"acquired": False, "lock_holder": ..., "acquired_at": ...}`
    - On release failure, log to stderr and return `{"released": False, "error": ...}`
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 1.4 Verify `src/redshift_agents/models.py` is unchanged — confirm all dataclasses (`WLMQueueMetrics`, `ClusterSummary`, `AssessmentResult`, `WorkgroupSpec`, `DataSharingConfig`, `ArchitectureResult`, `MigrationStep`, `ExecutionResult`, `ClusterLock`, `AuditEvent`) are present and unmodified
    - _Requirements: 8.1, 8.2, 8.3_

- [x] 2. Create Lambda handler functions
  - [x] 2.1 Create `src/redshift_agents/lambdas/assessment_handler.py` — Lambda handler that receives Bedrock Agent action group invocation events, extracts `apiPath` and `parameters`, dispatches to `listRedshiftClusters`, `analyzeRedshiftCluster`, `getClusterMetrics`, `getWlmConfiguration` tool functions, and returns the Bedrock Agent action group response format (`messageVersion`, `response.actionGroup`, `response.apiPath`, `response.httpMethod`, `response.httpStatusCode=200`, `response.responseBody.application/json.body`)
    - Extract `user_id` from parameters and pass to every tool function
    - Wrap dispatch in try/except for unexpected errors, returning `{"error": "Unexpected: ..."}` in the response body
    - Call `emit_audit_event` with `event_type="tool_invocation"` and `agent_name="assessment"` for every invocation
    - Catch `emit_audit_event` failures, log to stderr, continue processing
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 6.1, 6.2, 6.3_

  - [x] 2.2 Create `src/redshift_agents/lambdas/execution_handler.py` — Lambda handler dispatching to `executeRedshiftQuery`, `createServerlessNamespace`, `createServerlessWorkgroup`, `restoreSnapshotToServerless`, `setupDataSharing`
    - Same event parsing, response format, audit logging, and error handling pattern as assessment handler
    - Include STS `AssumeRole` with session tags (`PrincipalTag/user={user_id}`) for data-plane operations
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 6.1, 6.2, 6.3, 15.6_

  - [x] 2.3 Create `src/redshift_agents/lambdas/cluster_lock_handler.py` — Lambda handler dispatching to `acquireClusterLock` and `releaseClusterLock`
    - Same event parsing and response format pattern
    - _Requirements: 1.1, 7.1, 7.2, 7.3, 7.5_

  - [x] 2.4 Create `src/redshift_agents/lambdas/__init__.py` and ensure `audit_logger`, `models`, and `cluster_lock` modules are importable from the Lambda handler code
    - _Requirements: 1.7_

  - [x] 2.5 Write property test for Lambda handler event parsing and response format
    - **Property 1: Lambda handler event parsing and response format**
    - **Validates: Requirements 1.1, 11.5**

  - [x] 2.6 Write property test for Lambda handler error responses
    - **Property 2: Lambda handler error responses preserve structured format**
    - **Validates: Requirements 1.5**

  - [x] 2.7 Write property test for identity propagation through Lambda handlers
    - **Property 3: Identity propagation through Lambda handlers**
    - **Validates: Requirements 1.3, 6.2, 10.3, 10.4**

  - [x] 2.8 Write property test for audit event on every tool invocation
    - **Property 4: Audit event emitted for every tool invocation**
    - **Validates: Requirements 1.4, 6.1, 14.1**

  - [x] 2.9 Write property test for audit event schema validity
    - **Property 5: Audit event schema validity**
    - **Validates: Requirements 6.4, 6.5, 14.2, 14.5**

  - [x] 2.10 Write property test for audit failure resilience
    - **Property 6: Audit failure resilience**
    - **Validates: Requirements 6.3**

- [x] 3. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Create OpenAPI schemas for action groups
  - [x] 4.1 Create `src/redshift_agents/schemas/assessment-tools-openapi.json` — OpenAPI 3.0 schema defining operations for `listRedshiftClusters`, `analyzeRedshiftCluster`, `getClusterMetrics`, `getWlmConfiguration` with parameters matching existing tool signatures (`cluster_id`, `region`, `user_id`, `hours`), optional parameters marked with defaults, and response schemas including error responses
    - _Requirements: 2.1, 2.4, 2.5_

  - [x] 4.2 Create `src/redshift_agents/schemas/execution-tools-openapi.json` — OpenAPI 3.0 schema defining operations for `executeRedshiftQuery`, `createServerlessNamespace`, `createServerlessWorkgroup`, `restoreSnapshotToServerless`, `setupDataSharing`
    - _Requirements: 2.2, 2.4, 2.5_

  - [x] 4.3 Create `src/redshift_agents/schemas/cluster-lock-openapi.json` — OpenAPI 3.0 schema defining operations for `acquireClusterLock` and `releaseClusterLock` with parameters `cluster_id`, `user_id`, `region`
    - _Requirements: 2.3, 2.4, 2.5_

- [x] 5. Create CDK stack for infrastructure
  - [x] 5.1 Create `src/redshift_agents/cdk/app.py` and `src/redshift_agents/cdk/stack.py` — CDK app entry point and main stack class (`RedshiftModernizationStack`)
    - Initialize CDK app, define stack with configurable foundation model via CDK context
    - _Requirements: 9.1_

  - [x] 5.2 Add DynamoDB lock table to CDK stack — `redshift_modernization_locks` table with partition key `cluster_id` (String) and TTL on `ttl` attribute
    - _Requirements: 7.4, 9.5_

  - [x] 5.3 Add Lambda functions to CDK stack — create 3 Lambda functions (assessment-tools, execution-tools, cluster-lock) with Python 3.12 runtime, appropriate memory (256MB/256MB/128MB) and timeout (60s/120s/30s) settings, bundling `audit_logger`, `models`, `cluster_lock` modules in deployment packages
    - _Requirements: 1.6, 1.7, 9.1_

  - [x] 5.4 Add IAM execution roles for Lambda functions — least-privilege per function:
    - Assessment: `redshift:DescribeClusters`, `redshift-data:ExecuteStatement/DescribeStatement/GetStatementResult`, `cloudwatch:GetMetricStatistics`, CloudWatch Logs
    - Execution: `redshift-data:*`, `redshift-serverless:Create*/Update*/GetNamespace`, `redshift:RestoreFromClusterSnapshot`, CloudWatch Logs
    - Cluster lock: `dynamodb:PutItem/DeleteItem/GetItem` scoped to lock table ARN, CloudWatch Logs
    - _Requirements: 9.2, 12.1, 12.2, 12.3, 12.4_

  - [x] 5.5 Add Bedrock Agent resources to CDK stack — create Assessment Agent, Architecture Agent, Execution Agent, and Orchestrator (Supervisor) Agent, each with instruction prompts equivalent to existing system prompts, action group associations pointing to Lambda functions, and prepared aliases
    - Assessment Agent: assessment action group → assessment-tools Lambda
    - Architecture Agent: assessment action group + execution action group
    - Execution Agent: execution action group → execution-tools Lambda
    - Orchestrator: cluster lock action group (direct), collaborator associations to all 3 sub-agents with `relayConversationHistory: ENABLED`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.5_

  - [x] 5.6 Add Bedrock Agent IAM roles — `bedrock:InvokeModel` for foundation model, `lambda:InvokeFunction` scoped to specific Lambda ARNs per agent
    - _Requirements: 9.6, 12.5_

  - [x] 5.7 Add Cognito User Pool, App Client, Identity Pool, and Groups to CDK stack
    - User Pool: email-based sign-up/sign-in, password policy (min 8, uppercase, lowercase, number, symbol), email verification
    - App Client: `USER_PASSWORD_AUTH` + `USER_SRP_AUTH`, no client secret (public client)
    - Identity Pool: accepts User Pool JWT, maps to IAM roles by group
    - Groups: `redshift-admin` (full access), `redshift-viewer` (read-only)
    - IAM roles for groups with trust policy for `cognito-identity.amazonaws.com` conditioned on Identity Pool
    - _Requirements: 5.1, 5.2, 5.9, 15.1, 15.2, 15.3, 15.4, 15.8_

  - [x] 5.8 Add IAM roles for Cognito groups
    - `redshift-admin` role: full Redshift, Redshift Serverless, Redshift Data API, CloudWatch, DynamoDB lock, `bedrock:InvokeAgent`
    - `redshift-viewer` role: read-only Redshift (`redshift:Describe*`), Redshift Data API read, CloudWatch read, `bedrock:InvokeAgent` — NO `redshift-serverless:Create*`, NO DynamoDB write
    - _Requirements: 15.3, 15.4, 15.8_

  - [x] 5.9 Add CloudFormation outputs — Orchestrator Agent ID, Orchestrator Alias ID, Cognito User Pool ID, App Client ID, Identity Pool ID
    - _Requirements: 5.9, 9.7, 15.10_

  - [x] 5.10 Add `cdk.json` and `requirements.txt` for CDK project, add CDK dependencies
    - _Requirements: 9.1_

- [x] 6. Checkpoint — Ensure CDK stack synthesizes successfully
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Update Streamlit UI for Cognito authentication
  - [x] 7.1 Add Cognito sign-in form to `src/redshift_agents/ui/app.py` — username/email + password fields, shown before chat interface, call `InitiateAuth(AuthFlow=USER_PASSWORD_AUTH)`, store JWT tokens (ID, access, refresh) in `st.session_state`
    - _Requirements: 5.3, 5.4_

  - [x] 7.2 Implement user_id extraction from Cognito JWT — decode ID token, extract `cognito:username` claim (fallback to `email`), remove manual "User ID" text input from sidebar, display authenticated identity in sidebar
    - _Requirements: 5.5, 5.6, 5.8, 10.1_

  - [x] 7.3 Implement Identity Pool credential exchange — call `GetId` + `GetCredentialsForIdentity` with JWT, create `boto3.Session` with temporary credentials, use for all `invoke_agent` calls
    - _Requirements: 15.5, 5a.1_

  - [x] 7.4 Implement token refresh — when access token expires, use refresh token to obtain new tokens; if refresh fails, redirect to sign-in form
    - _Requirements: 5.7_

  - [x] 7.5 Update `invoke_agent` call — include Cognito-derived `user_id` in `inputText` payload (user cannot override), use Identity Pool credentials, update env vars to include `COGNITO_USER_POOL_ID`, `COGNITO_APP_CLIENT_ID`, `COGNITO_IDENTITY_POOL_ID`
    - _Requirements: 5a.1, 5a.2, 5a.3, 5a.4, 10.1, 10.6_

  - [x] 7.6 Write property test for Cognito JWT user_id extraction
    - **Property 7: Cognito JWT user_id extraction**
    - **Validates: Requirements 5.5, 10.1, 5a.3**

- [x] 8. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Update test suite for Lambda handler architecture
  - [x] 9.1 Remove `src/redshift_agents/tests/conftest.py` stubs for `strands` and `bedrock_agentcore` modules, add `build_action_group_event` and `parse_response_body` test helpers
    - _Requirements: 11.4, 13.4_

  - [x] 9.2 Rewrite `src/redshift_agents/tests/test_redshift_tools.py` — update tests to invoke Lambda handler functions with action group events instead of `@tool` functions, mock boto3 calls, assert on Bedrock Agent response format
    - _Requirements: 11.1, 11.2, 11.5_

  - [x] 9.3 Rewrite `src/redshift_agents/tests/test_audit_logger.py` — test `emit_audit_event` as standalone function, verify all required fields, ISO 8601 timestamps, event_type values
    - _Requirements: 11.1, 11.2_

  - [x] 9.4 Rewrite `src/redshift_agents/tests/test_cluster_lock.py` — test cluster lock Lambda handler with action group events, verify DynamoDB conditional write logic, lock/unlock lifecycle, contention response
    - _Requirements: 11.1, 11.2, 11.5_

  - [x] 9.5 Rewrite `src/redshift_agents/tests/test_assessment.py` — test assessment Lambda handler dispatch for all 4 operations via action group events
    - _Requirements: 11.1, 11.5_

  - [x] 9.6 Rewrite `src/redshift_agents/tests/test_execution.py` — test execution Lambda handler dispatch for all 5 operations via action group events, including STS AssumeRole with session tags
    - _Requirements: 11.1, 11.5, 11.6_

  - [x] 9.7 Update `src/redshift_agents/tests/test_orchestrator.py` — remove Strands/AgentCore references, test orchestrator instruction prompt content and collaborator configuration
    - _Requirements: 11.1, 11.4_

  - [x] 9.8 Write property tests for assessment tool correctness (Properties 8–11)
    - **Property 8: Cluster listing returns all clusters in region**
    - **Property 9: Cluster configuration output contains all required fields**
    - **Property 10: CloudWatch metrics output contains all required metric categories**
    - **Property 11: WLM per-queue metrics are complete**
    - **Validates: Requirements 1.1, 1.2, 11.3, 11.6**

  - [x] 9.9 Write property tests for architecture output correctness (Properties 12–15)
    - **Property 12: Workgroup count matches WLM queue mapping rules**
    - **Property 13: All workgroup RPUs are at least 32**
    - **Property 14: Architecture pattern is one of three valid values**
    - **Property 15: Architecture output includes cost estimates and migration complexity**
    - **Validates: Requirements 1.2, 8.1, 11.3, 11.6**

  - [x] 9.10 Write property tests for execution correctness (Properties 16–19)
    - **Property 16: Execution workgroup RPUs match architecture spec**
    - **Property 17: Data sharing configured if and only if hub-and-spoke**
    - **Property 18: Migration plan covers all source WLM queues**
    - **Property 19: Every execution step has a rollback procedure**
    - **Validates: Requirements 1.2, 8.1, 11.3, 11.6**

  - [x] 9.11 Write property tests for cluster lock correctness (Properties 20–21)
    - **Property 20: Cluster lock mutual exclusion**
    - **Property 21: Lock denial includes holder identity and timestamp**
    - **Validates: Requirements 7.1, 7.2, 11.3, 11.6**

  - [x] 9.12 Write property tests for cross-cutting concerns (Properties 22–23)
    - **Property 22: Tools pass region parameter to boto3 client**
    - **Property 23: STS AssumeRole includes user session tags**
    - **Validates: Requirements 1.2, 15.6, 11.3, 11.6**

- [x] 10. Remove Strands and AgentCore dependencies
  - [x] 10.1 Update `src/redshift_agents/requirements.txt` — remove `strands-agents`, `bedrock-agentcore`, and related packages; add `aws-cdk-lib`, `constructs` for CDK
    - _Requirements: 13.1_

  - [x] 10.2 Remove or replace `src/redshift_agents/deploy-agentcore.sh` with CDK deployment instructions/script (`cdk deploy`)
    - _Requirements: 13.3_

  - [x] 10.3 Remove Strands/AgentCore imports from `src/redshift_agents/orchestrator/orchestrator.py`, `src/redshift_agents/subagents/assessment.py`, `src/redshift_agents/subagents/architecture.py`, `src/redshift_agents/subagents/execution.py` — these modules can be archived or replaced with agent instruction prompt constants used by CDK
    - _Requirements: 13.2, 13.5_

  - [x] 10.4 Update `src/redshift_agents/tests/requirements-test.txt` — remove any Strands/AgentCore test dependencies
    - _Requirements: 13.1, 13.4_

  - [x] 10.5 Update `src/redshift_agents/.env.example` — add `COGNITO_USER_POOL_ID`, `COGNITO_APP_CLIENT_ID`, `COGNITO_IDENTITY_POOL_ID`; keep `ORCHESTRATOR_AGENT_ID`, `ORCHESTRATOR_AGENT_ALIAS_ID`
    - _Requirements: 5.9, 5a.2_

- [x] 11. Wire everything together and validate
  - [x] 11.1 Ensure all Lambda handlers import from the refactored tool modules, audit logger, and models correctly — verify import paths work for both local testing and Lambda deployment packaging
    - _Requirements: 1.7_

  - [x] 11.2 Ensure CDK stack references the correct Lambda handler entry points, OpenAPI schema file paths, and agent instruction prompts
    - _Requirements: 9.3, 9.4_

  - [x] 11.3 Update `src/redshift_agents/ui/requirements.txt` — add `boto3`, `pyjwt` (or `python-jose`) for JWT decoding, Cognito client dependencies
    - _Requirements: 5.3, 5.5_

- [x] 12. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (Properties 1–23 from design)
- Unit tests validate specific examples and edge cases
- The design uses Python throughout — all implementation tasks use Python
- Existing tool logic, data models, audit logger, and cluster lock are preserved; only the framework wiring changes
