# Requirements: Bedrock Agents Rewrite

## Introduction

Rewrite the Redshift Modernization Agents system from Strands Agents + Bedrock AgentCore to fully managed Amazon Bedrock Agents. Each current `@tool` function becomes a Lambda function (action group handler). Each subagent becomes a Bedrock Agent with action groups pointing to those Lambdas. The orchestrator becomes a Bedrock supervisor agent using native multi-agent collaboration (`AssociateAgentCollaborator`). Infrastructure is provisioned via AWS CDK. The Streamlit chat UI, audit logger, cluster lock mechanism, data models, and all existing observability and identity propagation requirements are preserved.

## Glossary

- **Bedrock_Agent**: A fully managed Amazon Bedrock Agent resource (`bedrock:CreateAgent`) with an instruction prompt, a foundation model, and one or more action groups.
- **Action_Group**: A Bedrock Agent action group that maps agent capabilities to a Lambda function handler. Defined by an OpenAPI schema describing the available operations.
- **Lambda_Handler**: An AWS Lambda function that implements one or more tool operations previously defined as `@tool` functions. Receives Bedrock Agent action group invocation events and returns structured responses.
- **Supervisor_Agent**: A Bedrock Agent configured with `AssociateAgentCollaborator` to delegate tasks to sub-agents using native multi-agent collaboration.
- **Collaborator**: A sub-agent associated with a supervisor agent via `AssociateAgentCollaborator`, with a collaboration instruction and relay conversation history setting.
- **OpenAPI_Schema**: An OpenAPI 3.0 specification that describes the operations available in an action group, including request/response schemas and parameter definitions.
- **CDK_Stack**: An AWS CDK construct that provisions all infrastructure: Lambda functions, Bedrock Agents, IAM roles, DynamoDB tables, and agent-collaborator associations.
- **Orchestrator**: The supervisor Bedrock Agent that coordinates the three-phase modernization workflow, enforces approval gates, and manages cluster locks.
- **Assessment_Agent**: A Bedrock Agent collaborator responsible for cluster discovery, WLM queue analysis, and CloudWatch metrics retrieval.
- **Architecture_Agent**: A Bedrock Agent collaborator responsible for workgroup design, RPU sizing, and architecture pattern selection.
- **Execution_Agent**: A Bedrock Agent collaborator responsible for creating Serverless resources, restoring snapshots, setting up data sharing, and validating performance.
- **Audit_Logger**: The `emit_audit_event` function that emits structured JSON audit events, preserved inside Lambda handlers.
- **Cluster_Lock**: The DynamoDB-based mutual exclusion mechanism that prevents concurrent operations on the same Redshift cluster.
- **Identity_Propagation**: The chain of authenticated `user_id` flowing from the Cognito-authenticated Streamlit UI through the supervisor agent, to collaborator agents, into Lambda handlers, and finally to the Redshift Data API `DbUser` parameter and audit logs. The `user_id` is derived server-side from the Cognito JWT token and cannot be spoofed.
- **Cognito_User_Pool**: An Amazon Cognito User Pool that authenticates users of the Streamlit chat UI. Users sign in with username/password (or federated identity) and receive a JWT token. The `user_id` is extracted from the token's `cognito:username` or `email` claim.
- **Cognito_App_Client**: A Cognito User Pool app client configured for the Streamlit UI, enabling the hosted UI sign-in flow or direct API authentication.
- **Cognito_Identity_Pool**: An Amazon Cognito Identity Pool (federated identities) that exchanges Cognito User Pool JWT tokens for temporary AWS STS credentials. The credentials are scoped to an IAM role determined by the user's Cognito group membership.
- **Cognito_Group**: A Cognito User Pool group (e.g., `redshift-admin`, `redshift-viewer`) that maps to an IAM role. Group membership determines what AWS actions the user is authorized to perform through the agent.
- **User_Scoped_Credentials**: Temporary AWS credentials obtained via Cognito Identity Pool that carry the user's identity as IAM session tags. Lambda handlers use these credentials (or assume a role with session tags) so that AWS API calls are authorized against the user's effective permissions, not the Lambda's own role.

## Requirements


### Requirement 1: Convert Tool Functions to Lambda Handlers

**User Story:** As a platform engineer, I want each `@tool` function converted to a Lambda function handler, so that Bedrock Agents can invoke them as action groups without depending on the Strands framework.

#### Acceptance Criteria

1. WHEN a Bedrock Agent invokes an action group, THE Lambda_Handler SHALL receive the action group invocation event, extract the API path and parameters, execute the corresponding tool logic, and return a structured response in the Bedrock Agent action group response format.
2. THE Lambda_Handler SHALL preserve the existing tool logic from `redshift_tools.py` including all boto3 calls, error handling patterns (returning `{"error": ...}` dicts), and parameter defaults (`region` defaulting to `us-east-1`).
3. THE Lambda_Handler SHALL accept `user_id` as a parameter in every operation and pass the value to `emit_audit_event(initiated_by=user_id)` and to the Redshift Data API as `DbUser=user_id`.
4. THE Lambda_Handler SHALL call `emit_audit_event` for every tool invocation, preserving the existing audit event schema (`event_type`, `agent_name`, `initiated_by`, `cluster_id`, `region`, `details`).
5. WHEN a Lambda_Handler encounters an exception from a boto3 call, THE Lambda_Handler SHALL catch the exception and return a structured error response containing the error message and input parameters, matching the existing error dict pattern.
6. THE CDK_Stack SHALL create one Lambda function per logical tool grouping: an assessment tools Lambda (covering `list_redshift_clusters`, `analyze_redshift_cluster`, `get_cluster_metrics`, `get_wlm_configuration`), an execution tools Lambda (covering `execute_redshift_query`, `create_serverless_namespace`, `create_serverless_workgroup`, `restore_snapshot_to_serverless`, `setup_data_sharing`), and a cluster lock Lambda (covering `acquire_lock`, `release_lock`).
7. THE Lambda_Handler SHALL include the `audit_logger` module (`emit_audit_event`) and the `models.py` dataclasses as bundled dependencies in the Lambda deployment package.

### Requirement 2: Define OpenAPI Schemas for Action Groups

**User Story:** As a platform engineer, I want OpenAPI 3.0 schemas for each action group, so that Bedrock Agents know the available operations, parameters, and response formats for each Lambda handler.

#### Acceptance Criteria

1. THE OpenAPI_Schema for the assessment action group SHALL define operations for `listRedshiftClusters`, `analyzeRedshiftCluster`, `getClusterMetrics`, and `getWlmConfiguration`, with request parameters matching the existing tool function signatures (`cluster_id`, `region`, `user_id`, `hours`).
2. THE OpenAPI_Schema for the execution action group SHALL define operations for `executeRedshiftQuery`, `createServerlessNamespace`, `createServerlessWorkgroup`, `restoreSnapshotToServerless`, and `setupDataSharing`, with request parameters matching the existing tool function signatures.
3. THE OpenAPI_Schema for the cluster lock action group SHALL define operations for `acquireClusterLock` and `releaseClusterLock`, with parameters `cluster_id`, `user_id`, and `region`.
4. WHEN a parameter has a default value in the existing tool function, THE OpenAPI_Schema SHALL mark that parameter as optional and document the default value in the schema description.
5. THE OpenAPI_Schema SHALL define response schemas that match the existing tool return types, including both success responses and error responses with the `error` key pattern.

### Requirement 3: Create Bedrock Sub-Agents with Action Groups

**User Story:** As a platform engineer, I want each subagent (assessment, architecture, execution) created as a fully managed Bedrock Agent with action groups pointing to the corresponding Lambda functions, so that the system uses native Bedrock Agent capabilities instead of Strands framework.

#### Acceptance Criteria

1. THE CDK_Stack SHALL create the Assessment_Agent as a Bedrock Agent resource with the assessment action group pointing to the assessment tools Lambda, and an instruction prompt equivalent to the existing `ASSESSMENT_SYSTEM_PROMPT`.
2. THE CDK_Stack SHALL create the Architecture_Agent as a Bedrock Agent resource with both the assessment action group (for `getWlmConfiguration`) and the execution action group (for `executeRedshiftQuery`) as action groups, and an instruction prompt equivalent to the existing `ARCHITECTURE_SYSTEM_PROMPT`.
3. THE CDK_Stack SHALL create the Execution_Agent as a Bedrock Agent resource with the execution action group pointing to the execution tools Lambda, and an instruction prompt equivalent to the existing `EXECUTION_SYSTEM_PROMPT`.
4. THE CDK_Stack SHALL create a prepared agent alias for each Bedrock Agent so that the supervisor agent and the Streamlit UI can invoke them.
5. WHEN a Bedrock Agent receives a request, THE Bedrock_Agent SHALL use the instruction prompt to reason about which action group operations to invoke, matching the existing agent behavior defined in the system prompts.

### Requirement 4: Create Supervisor Agent with Multi-Agent Collaboration

**User Story:** As a platform engineer, I want the orchestrator created as a Bedrock supervisor agent using `AssociateAgentCollaborator`, so that it delegates to sub-agents using native multi-agent collaboration instead of hand-rolled `invoke_agent` calls.

#### Acceptance Criteria

1. THE CDK_Stack SHALL create the Orchestrator as a Bedrock Agent resource with an instruction prompt equivalent to the existing `ORCHESTRATOR_SYSTEM_PROMPT`, including the three-phase workflow, approval gate rules, cluster locking behavior, and identity propagation requirements.
2. THE CDK_Stack SHALL associate the Assessment_Agent, Architecture_Agent, and Execution_Agent as collaborators on the Orchestrator using `AssociateAgentCollaborator`, each with a collaboration instruction describing when and how to delegate to that sub-agent.
3. THE CDK_Stack SHALL associate the cluster lock action group directly on the Orchestrator as an action group (not via a collaborator), so the Orchestrator can acquire and release cluster locks as direct tool calls.
4. WHEN the Orchestrator delegates to a collaborator, THE Supervisor_Agent SHALL pass the conversation context including `user_id`, `cluster_id`, `region`, and `customer_account_id` to the collaborator for identity propagation.
5. THE Supervisor_Agent SHALL enforce approval gates between phases: the instruction prompt SHALL instruct the Orchestrator to ask for explicit user approval before delegating from assessment to architecture and from architecture to execution.
6. WHEN the Orchestrator delegates to a collaborator and the collaborator returns an error, THE Supervisor_Agent SHALL surface the error to the user and offer to retry, matching the existing error handling behavior.

### Requirement 5: Add Cognito Authentication to Streamlit Chat UI

**User Story:** As a security engineer, I want the Streamlit chat UI to authenticate users via Amazon Cognito, so that `user_id` is derived from a cryptographically signed JWT token and cannot be spoofed.

#### Acceptance Criteria

1. THE CDK_Stack SHALL create a Cognito_User_Pool with email-based sign-up and sign-in, password policies, and email verification.
2. THE CDK_Stack SHALL create a Cognito_App_Client for the Streamlit UI with the `USER_PASSWORD_AUTH` and `USER_SRP_AUTH` authentication flows enabled.
3. THE Streamlit UI SHALL present a sign-in form (username/email + password) before granting access to the chat interface.
4. WHEN the user signs in successfully, THE Streamlit UI SHALL store the Cognito JWT tokens (ID token, access token, refresh token) in the Streamlit session state.
5. THE Streamlit UI SHALL extract `user_id` from the Cognito ID token's `cognito:username` claim (or `email` claim as fallback) — NOT from user-supplied text input.
6. THE Streamlit UI SHALL remove the manual "User ID" text input field from the sidebar, since identity is now derived from the authenticated session.
7. WHEN the user's access token expires, THE Streamlit UI SHALL use the refresh token to obtain new tokens transparently, or prompt the user to sign in again.
8. THE Streamlit UI SHALL display the authenticated user's identity (email or username) in the sidebar so the user knows which identity is being used.
9. THE CDK_Stack SHALL output the Cognito User Pool ID and App Client ID as CloudFormation outputs so the Streamlit UI can be configured.

### Requirement 5a: Preserve Streamlit Chat UI Functionality

**User Story:** As a developer, I want the Streamlit chat UI to continue working with the new Bedrock Agents, so that the user experience is unchanged apart from the addition of sign-in.

#### Acceptance Criteria

1. THE Streamlit UI SHALL continue to invoke the orchestrator via `boto3.client("bedrock-agent-runtime").invoke_agent()` using the Orchestrator's agent ID and alias ID.
2. THE Streamlit UI SHALL require no code changes to the chat logic beyond updating the `ORCHESTRATOR_AGENT_ID` and `ORCHESTRATOR_AGENT_ALIAS_ID` environment variables to point to the new Bedrock Agent.
3. WHEN the user sends a message, THE Streamlit UI SHALL include the Cognito-derived `user_id` in the `inputText` payload — the user cannot override or modify this value.
4. THE Streamlit UI SHALL continue to stream responses from the orchestrator using the `completion` event stream, matching the existing response handling logic.

### Requirement 6: Preserve Audit Logger in Lambda Handlers

**User Story:** As a platform engineer, I want the audit logger (`emit_audit_event`) preserved inside Lambda functions, so that all existing fleet observability and audit traceability requirements continue to be met.

#### Acceptance Criteria

1. THE Lambda_Handler SHALL import and call `emit_audit_event` for every tool invocation, emitting structured JSON audit events to the `redshift_modernization_audit` logger.
2. THE Lambda_Handler SHALL propagate `user_id` from the action group invocation event to `emit_audit_event(initiated_by=user_id)` for every operation.
3. WHEN `emit_audit_event` fails inside a Lambda_Handler, THE Lambda_Handler SHALL catch the exception, log the failure to stderr, and continue processing the tool invocation without blocking.
4. THE Lambda_Handler SHALL emit audit events with all required fields: `timestamp` (ISO 8601), `event_type`, `agent_name`, `customer_account_id`, `initiated_by`, `cluster_id`, `region`, and `details`.
5. THE audit event `event_type` values SHALL remain unchanged: `agent_start`, `tool_invocation`, `workflow_start`, `workflow_complete`, `phase_start`, `phase_complete`, `error`.

### Requirement 7: Preserve Cluster Lock Mechanism

**User Story:** As a platform engineer, I want the DynamoDB cluster lock mechanism preserved and wired as an action group on the supervisor agent, so that concurrent cluster operations are still prevented.

#### Acceptance Criteria

1. THE cluster lock Lambda_Handler SHALL implement `acquire_lock` and `release_lock` with the same DynamoDB conditional write logic (`attribute_not_exists(cluster_id)`) and 24-hour TTL safety net.
2. WHEN a lock acquisition fails due to contention (`ConditionalCheckFailedException`), THE cluster lock Lambda_Handler SHALL return the current lock holder's `lock_holder` and `acquired_at` values.
3. WHEN a lock release fails, THE cluster lock Lambda_Handler SHALL log the error to stderr and return a failure response without blocking, matching the existing TTL safety net behavior.
4. THE CDK_Stack SHALL create the DynamoDB lock table (`redshift_modernization_locks`) with `cluster_id` as the partition key and TTL enabled on the `ttl` attribute.
5. THE CDK_Stack SHALL wire the cluster lock action group directly on the Orchestrator so the supervisor agent can call `acquireClusterLock` and `releaseClusterLock` as direct actions.


### Requirement 8: Preserve Data Models

**User Story:** As a developer, I want the existing data models in `models.py` preserved and used by Lambda handlers, so that structured output schemas remain consistent across the rewrite.

#### Acceptance Criteria

1. THE Lambda_Handler deployment packages SHALL include `models.py` with all existing dataclasses: `WLMQueueMetrics`, `ClusterSummary`, `AssessmentResult`, `WorkgroupSpec`, `DataSharingConfig`, `ArchitectureResult`, `MigrationStep`, `ExecutionResult`, `ClusterLock`, and `AuditEvent`.
2. THE Lambda_Handler SHALL use the `AuditEvent` dataclass when constructing audit events via `emit_audit_event`, matching the existing audit logger behavior.
3. THE data model definitions SHALL remain unchanged from the current `models.py` to maintain backward compatibility with any downstream consumers.

### Requirement 9: CDK Infrastructure-as-Code Deployment

**User Story:** As a platform engineer, I want all infrastructure provisioned via AWS CDK, so that the entire system (Lambda functions, Bedrock Agents, IAM roles, DynamoDB tables, agent-collaborator associations) is reproducible and version-controlled.

#### Acceptance Criteria

1. THE CDK_Stack SHALL create Lambda functions for each tool grouping (assessment tools, execution tools, cluster lock) with Python 3.12 runtime and appropriate memory/timeout settings.
2. THE CDK_Stack SHALL create IAM execution roles for each Lambda function scoped to least-privilege: the assessment Lambda role SHALL have read-only Redshift (`redshift:Describe*`), Redshift Data API read (`redshift-data:ExecuteStatement`, `redshift-data:DescribeStatement`, `redshift-data:GetStatementResult`), and CloudWatch read (`cloudwatch:GetMetricStatistics`) permissions; the execution Lambda role SHALL additionally have Redshift Serverless write permissions (`redshift-serverless:Create*`, `redshift-serverless:Update*`, `redshift-serverless:GetNamespace`, `redshift:RestoreFromClusterSnapshot`); the cluster lock Lambda role SHALL have DynamoDB permissions (`dynamodb:PutItem`, `dynamodb:DeleteItem`, `dynamodb:GetItem`) on the lock table.
3. THE CDK_Stack SHALL create Bedrock Agent resources for the Orchestrator, Assessment_Agent, Architecture_Agent, and Execution_Agent, each with the appropriate action groups and instruction prompts.
4. THE CDK_Stack SHALL create agent aliases and associate collaborators on the Orchestrator using `AssociateAgentCollaborator` for each sub-agent.
5. THE CDK_Stack SHALL create the DynamoDB lock table with partition key `cluster_id` (String) and TTL on the `ttl` attribute.
6. THE CDK_Stack SHALL create a Bedrock Agent IAM role for each agent with `bedrock:InvokeModel` permission for the configured foundation model and `lambda:InvokeFunction` permission for the agent's action group Lambdas.
7. THE CDK_Stack SHALL output the Orchestrator agent ID, alias ID, Cognito User Pool ID, and Cognito App Client ID as CloudFormation outputs so the Streamlit UI can be configured.

### Requirement 10: Preserve Identity Propagation with Cognito-Derived Identity

**User Story:** As a security engineer, I want end-to-end identity propagation using the Cognito-authenticated identity, so that every action is traceable to the verified individual who initiated it and spoofing is impossible.

#### Acceptance Criteria

1. WHEN the Streamlit UI sends a request, THE Streamlit UI SHALL extract `user_id` from the Cognito ID token's `cognito:username` claim and include it in the `inputText` payload to the Orchestrator — the user cannot supply or override this value.
2. WHEN the Orchestrator delegates to a collaborator, THE Supervisor_Agent SHALL include `user_id` in the conversation context passed to the collaborator.
3. WHEN a Lambda_Handler executes a Redshift Data API call, THE Lambda_Handler SHALL pass `DbUser=user_id` to `execute_statement`, so that Redshift audit logs (`STL_CONNECTION_LOG`, `STL_USERLOG`) attribute queries to the individual.
4. WHEN a Lambda_Handler emits an audit event, THE Lambda_Handler SHALL set `initiated_by=user_id` on the audit event.
5. THE identity propagation chain SHALL be reconstructable: Cognito-authenticated user → Orchestrator session → collaborator delegation → Lambda invocation → audit event (`initiated_by`) → Redshift Data API (`DbUser`) → Redshift audit logs → CloudTrail events.
6. THE `user_id` value used throughout the chain SHALL always originate from the Cognito JWT token, never from user-supplied text input, ensuring the identity cannot be spoofed.

### Requirement 11: Update Tests for Lambda Handlers

**User Story:** As a developer, I want the test suite updated to test Lambda handler functions instead of `@tool` functions, so that the 68 existing tests validate the new architecture.

#### Acceptance Criteria

1. WHEN testing a Lambda_Handler, THE test SHALL construct a Bedrock Agent action group invocation event with the appropriate `apiPath`, `httpMethod`, and `parameters`, invoke the Lambda handler function, and assert on the response body.
2. THE test suite SHALL mock all AWS API calls via `unittest.mock.patch` on `boto3.client`, requiring no AWS credentials for local testing.
3. THE test suite SHALL preserve all 19 property-based tests using `hypothesis` with `@settings(max_examples=100)`, adapted to invoke Lambda handler functions instead of `@tool` functions.
4. THE test suite SHALL remove the `conftest.py` stubs for `strands` and `bedrock_agentcore` modules, since those dependencies are removed.
5. THE test suite SHALL validate that Lambda handlers correctly parse action group invocation events and return responses in the Bedrock Agent action group response format.
6. WHEN a property-based test generates random inputs, THE test SHALL construct valid action group invocation events from those inputs and verify the same correctness properties defined in the existing design document.

### Requirement 12: Update IAM Policies for Lambda Execution Roles

**User Story:** As a security engineer, I want IAM policies for Lambda execution roles scoped to least-privilege, so that each Lambda function has only the permissions it needs.

#### Acceptance Criteria

1. THE assessment Lambda execution role SHALL have permissions for `redshift:DescribeClusters`, `redshift-data:ExecuteStatement`, `redshift-data:DescribeStatement`, `redshift-data:GetStatementResult`, and `cloudwatch:GetMetricStatistics`.
2. THE execution Lambda execution role SHALL have permissions for `redshift-data:ExecuteStatement`, `redshift-data:DescribeStatement`, `redshift-data:GetStatementResult`, `redshift-serverless:CreateNamespace`, `redshift-serverless:CreateWorkgroup`, `redshift-serverless:GetNamespace`, `redshift-serverless:RestoreFromSnapshot`, and `redshift:RestoreFromClusterSnapshot`.
3. THE cluster lock Lambda execution role SHALL have permissions for `dynamodb:PutItem`, `dynamodb:DeleteItem`, and `dynamodb:GetItem` scoped to the `redshift_modernization_locks` table ARN.
4. THE Lambda execution roles SHALL include `logs:CreateLogGroup`, `logs:CreateLogStream`, and `logs:PutLogEvents` permissions for CloudWatch Logs.
5. THE Bedrock Agent roles SHALL have `lambda:InvokeFunction` permission scoped to the specific Lambda function ARNs used by their action groups.

### Requirement 13: Remove Strands and AgentCore Dependencies

**User Story:** As a developer, I want all Strands Agent and Bedrock AgentCore dependencies removed, so that the codebase has no unused framework dependencies.

#### Acceptance Criteria

1. THE `requirements.txt` SHALL remove `strands-agents` and `bedrock-agentcore` (and any related packages) from the dependency list.
2. THE Lambda_Handler source code SHALL contain no imports from `strands`, `strands.tools`, or `bedrock_agentcore`.
3. THE `deploy-agentcore.sh` script SHALL be replaced by CDK deployment commands (`cdk deploy`).
4. THE `conftest.py` test stubs for `strands` and `bedrock_agentcore` modules SHALL be removed.
5. THE Lambda_Handler source code SHALL not use the `@tool` decorator; tool logic SHALL be plain Python functions called by the Lambda handler's event dispatcher.

### Requirement 14: Preserve Observability Requirements

**User Story:** As a platform engineer, I want all existing observability requirements (NFR-5, NFR-6, NFR-7 from the original spec) preserved in the new architecture, so that fleet audit, structured logging, and identity traceability continue to work.

#### Acceptance Criteria

1. THE Lambda_Handler SHALL emit structured JSON logs to CloudWatch Logs via the `redshift_modernization_audit` Python logger, matching the existing audit event schema.
2. THE Lambda_Handler SHALL include `customer_account_id`, `agent_name`, `event_type`, `cluster_id`, `region`, and ISO 8601 `timestamp` in every audit event.
3. THE CDK_Stack SHALL configure Lambda function log groups with appropriate retention policies.
4. WHEN the customer has opted in to cross-account log sharing, THE CloudWatch Logs subscription filter SHALL continue to forward audit events to the Redshift Service Team log destination.
5. THE audit event types SHALL remain: `agent_start`, `tool_invocation`, `workflow_start`, `workflow_complete`, `phase_start`, `phase_complete`, `error`.
6. THE identity propagation chain (Cognito-authenticated user → agent → Lambda → audit event → Redshift Data API → CloudTrail) SHALL be fully reconstructable from the logs, with `user_id` always originating from the Cognito JWT token.


### Requirement 15: User Authorization via Cognito Groups and IAM Role Scoping

**User Story:** As a security engineer, I want the system to enforce that users can only perform AWS actions they are authorized for, so that a read-only user cannot trigger resource creation and the agent cannot be used to escalate privileges.

#### Acceptance Criteria

1. THE CDK_Stack SHALL create a Cognito_Identity_Pool that accepts tokens from the Cognito_User_Pool and maps authenticated users to IAM roles based on Cognito group membership.
2. THE CDK_Stack SHALL create at least two Cognito_Groups with corresponding IAM roles: `redshift-admin` (full access: assessment + architecture + execution) and `redshift-viewer` (read-only: assessment only).
3. THE `redshift-viewer` IAM role SHALL have permissions limited to read-only Redshift operations (`redshift:Describe*`), Redshift Data API read (`redshift-data:ExecuteStatement` for SELECT queries only via IAM condition), CloudWatch read (`cloudwatch:GetMetricStatistics`), and `bedrock:InvokeAgent` for the Orchestrator. It SHALL NOT have permissions for `redshift-serverless:Create*`, `redshift-serverless:Update*`, `redshift:RestoreFromClusterSnapshot`, or DynamoDB write operations.
4. THE `redshift-admin` IAM role SHALL have permissions for all operations: read-only Redshift, Redshift Serverless write, Redshift Data API, CloudWatch read, DynamoDB lock operations, and `bedrock:InvokeAgent`.
5. THE Streamlit UI SHALL obtain temporary AWS credentials from the Cognito_Identity_Pool after authentication, and use those credentials (not hardcoded or environment-based credentials) to call `invoke_agent`.
6. WHEN a Lambda_Handler needs to perform an AWS action on behalf of the user, THE Lambda_Handler SHALL use STS `AssumeRole` with session tags (`PrincipalTag/user={user_id}`) to assume a role that is scoped to the user's authorized permissions, rather than using the Lambda's own execution role for data-plane operations.
7. WHEN a user in the `redshift-viewer` group attempts an action that requires write permissions (e.g., the execution phase), THE system SHALL return an access denied error from the AWS API call, and the agent SHALL surface this error to the user with a clear message explaining they lack the required permissions.
8. THE CDK_Stack SHALL create the IAM roles for Cognito groups with trust policies that allow `cognito-identity.amazonaws.com` to assume them, with conditions restricting assumption to the specific Identity Pool.
9. THE Orchestrator's instruction prompt SHALL include guidance that if a user's action fails with an access denied error, the agent should explain that the user may not have sufficient permissions and suggest contacting their administrator.
10. THE CDK_Stack SHALL output the Cognito Identity Pool ID as a CloudFormation output so the Streamlit UI can be configured.
