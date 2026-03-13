"""
CDK stack for the Redshift Modernization Agents system.

Provisions all infrastructure: DynamoDB lock table, Lambda functions,
Bedrock Agents (assessment, architecture, execution, orchestrator),
Cognito User Pool + Identity Pool, and IAM roles.

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7
"""
from __future__ import annotations

from pathlib import Path

import aws_cdk as cdk
from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from constructs import Construct

# Resolve paths relative to this file
_CDK_DIR = Path(__file__).resolve().parent
_SRC_DIR = _CDK_DIR.parent  # src/redshift_agents
_SCHEMAS_DIR = _SRC_DIR / "schemas"

# Directories/files to exclude from Lambda deployment packages
_LAMBDA_ASSET_EXCLUDES = [
    "cdk",
    "cdk/*",
    "tests",
    "tests/*",
    "ui",
    "ui/*",
    "iam",
    "iam/*",
    "schemas",
    "schemas/*",
    ".hypothesis",
    ".hypothesis/*",
    ".pytest_cache",
    ".pytest_cache/*",
    "__pycache__",
    "**/__pycache__",
    "**/__pycache__/*",
    "*.pyc",
    ".env",
    ".env.example",
    "deploy-agentcore.sh",
    "requirements.txt",
    "README.md",
    "setup_multi_agent.py",
]


def _extract_prompt(filepath: Path, variable_name: str) -> str:
    """Extract a triple-quoted string constant from a Python source file.

    This avoids importing the agent modules (which depend on boto3)
    at CDK synth time.  It finds ``VARIABLE = \"\"\"...\"\"\"`` and returns
    the content between the triple-quotes.
    """
    source = filepath.read_text(encoding="utf-8")
    # Find the assignment: VARIABLE_NAME = """..."""
    marker = f'{variable_name} = """'
    start = source.find(marker)
    if start == -1:
        raise ValueError(
            f"Could not find {variable_name} in {filepath}"
        )
    start += len(marker)
    end = source.find('"""', start)
    if end == -1:
        raise ValueError(
            f"Could not find closing triple-quote for {variable_name} in {filepath}"
        )
    return source[start:end]


# Extract system prompts from source files without importing the modules
ORCHESTRATOR_SYSTEM_PROMPT = _extract_prompt(
    _SRC_DIR / "orchestrator" / "orchestrator.py", "ORCHESTRATOR_SYSTEM_PROMPT"
)
ASSESSMENT_SYSTEM_PROMPT = _extract_prompt(
    _SRC_DIR / "subagents" / "assessment.py", "ASSESSMENT_SYSTEM_PROMPT"
)
ARCHITECTURE_SYSTEM_PROMPT = _extract_prompt(
    _SRC_DIR / "subagents" / "architecture.py", "ARCHITECTURE_SYSTEM_PROMPT"
)
EXECUTION_SYSTEM_PROMPT = _extract_prompt(
    _SRC_DIR / "subagents" / "execution.py", "EXECUTION_SYSTEM_PROMPT"
)


class RedshiftModernizationStack(Stack):
    """Main CDK stack for Redshift Modernization Agents."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Configurable foundation model via CDK context
        foundation_model = self.node.try_get_context("foundation_model") or (
            "anthropic.claude-3-5-sonnet-20241022-v2:0"
        )

        # ----- Task 5.2: DynamoDB lock table -----
        lock_table = self._create_lock_table()

        # ----- Task 5.3 + 5.4: Lambda functions with IAM roles -----
        assessment_lambda = self._create_assessment_lambda()
        execution_lambda = self._create_execution_lambda()
        cluster_lock_lambda = self._create_cluster_lock_lambda(lock_table)

        # ----- Task 5.6: Bedrock Agent IAM roles -----
        assessment_agent_role = self._create_agent_role(
            "AssessmentAgentRole", foundation_model, [assessment_lambda]
        )
        architecture_agent_role = self._create_agent_role(
            "ArchitectureAgentRole",
            foundation_model,
            [assessment_lambda, execution_lambda],
        )
        execution_agent_role = self._create_agent_role(
            "ExecutionAgentRole", foundation_model, [execution_lambda]
        )
        orchestrator_agent_role = self._create_agent_role(
            "OrchestratorAgentRole", foundation_model, [cluster_lock_lambda, assessment_lambda]
        )

        # ----- Task 5.5: Bedrock Agent resources -----
        agents = self._create_bedrock_agents(
            foundation_model=foundation_model,
            assessment_lambda=assessment_lambda,
            execution_lambda=execution_lambda,
            cluster_lock_lambda=cluster_lock_lambda,
            assessment_agent_role=assessment_agent_role,
            architecture_agent_role=architecture_agent_role,
            execution_agent_role=execution_agent_role,
            orchestrator_agent_role=orchestrator_agent_role,
        )

        # ----- Task 5.7 + 5.8: Cognito resources -----
        cognito_resources = self._create_cognito_resources(
            lock_table=lock_table,
            orchestrator_agent_id=agents["orchestrator"].ref,
        )

        # ----- Task 5.9: CloudFormation outputs -----
        self._create_outputs(agents, cognito_resources)

    # -----------------------------------------------------------------------
    # Task 5.2: DynamoDB lock table
    # -----------------------------------------------------------------------
    def _create_lock_table(self) -> dynamodb.Table:
        """Create the redshift_modernization_locks DynamoDB table."""
        return dynamodb.Table(
            self,
            "LockTable",
            table_name="redshift_modernization_locks",
            partition_key=dynamodb.Attribute(
                name="cluster_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl",
        )

    # -----------------------------------------------------------------------
    # Task 5.3 + 5.4: Lambda functions with least-privilege IAM
    # -----------------------------------------------------------------------
    def _create_assessment_lambda(self) -> _lambda.Function:
        """Create the assessment-tools Lambda function."""
        role = iam.Role(
            self,
            "AssessmentLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["redshift:DescribeClusters"],
                resources=["*"],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "redshift-data:ExecuteStatement",
                    "redshift-data:DescribeStatement",
                    "redshift-data:GetStatementResult",
                ],
                resources=["*"],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["cloudwatch:GetMetricStatistics"],
                resources=["*"],
            )
        )

        fn = _lambda.Function(
            self,
            "AssessmentToolsLambda",
            function_name="assessment-tools",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambdas.assessment_handler.handler",
            code=_lambda.Code.from_asset(
                str(_SRC_DIR), exclude=_LAMBDA_ASSET_EXCLUDES
            ),
            memory_size=256,
            timeout=Duration.seconds(60),
            role=role,
        )
        fn.grant_invoke(iam.ServicePrincipal("bedrock.amazonaws.com"))
        return fn

    def _create_execution_lambda(self) -> _lambda.Function:
        """Create the execution-tools Lambda function."""
        role = iam.Role(
            self,
            "ExecutionLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["redshift-data:*"],
                resources=["*"],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "redshift-serverless:CreateNamespace",
                    "redshift-serverless:CreateWorkgroup",
                    "redshift-serverless:UpdateNamespace",
                    "redshift-serverless:UpdateWorkgroup",
                    "redshift-serverless:GetNamespace",
                ],
                resources=["*"],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["redshift:RestoreFromClusterSnapshot"],
                resources=["*"],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["sts:AssumeRole", "sts:TagSession"],
                resources=["*"],
            )
        )

        fn = _lambda.Function(
            self,
            "ExecutionToolsLambda",
            function_name="execution-tools",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambdas.execution_handler.handler",
            code=_lambda.Code.from_asset(
                str(_SRC_DIR), exclude=_LAMBDA_ASSET_EXCLUDES
            ),
            memory_size=256,
            timeout=Duration.seconds(120),
            role=role,
        )
        fn.grant_invoke(iam.ServicePrincipal("bedrock.amazonaws.com"))
        return fn

    def _create_cluster_lock_lambda(
        self, lock_table: dynamodb.Table
    ) -> _lambda.Function:
        """Create the cluster-lock Lambda function."""
        role = iam.Role(
            self,
            "ClusterLockLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "dynamodb:PutItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:GetItem",
                ],
                resources=[lock_table.table_arn],
            )
        )

        fn = _lambda.Function(
            self,
            "ClusterLockLambda",
            function_name="cluster-lock",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambdas.cluster_lock_handler.handler",
            code=_lambda.Code.from_asset(
                str(_SRC_DIR), exclude=_LAMBDA_ASSET_EXCLUDES
            ),
            memory_size=128,
            timeout=Duration.seconds(30),
            role=role,
            environment={
                "LOCK_TABLE_NAME": lock_table.table_name,
            },
        )
        fn.grant_invoke(iam.ServicePrincipal("bedrock.amazonaws.com"))
        return fn

    # -----------------------------------------------------------------------
    # Task 5.6: Bedrock Agent IAM roles
    # -----------------------------------------------------------------------
    def _create_agent_role(
        self,
        role_id: str,
        foundation_model: str,
        lambda_functions: list[_lambda.Function],
    ) -> iam.Role:
        """Create an IAM role for a Bedrock Agent."""
        role = iam.Role(
            self,
            role_id,
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
        )
        # Allow invoking the foundation model
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/anthropic.claude-*",
                    "arn:aws:bedrock:*::foundation-model/us.anthropic.claude-*",
                    f"arn:aws:bedrock:*:*:inference-profile/{foundation_model}",
                ],
            )
        )
        # Allow invoking the specific Lambda functions for this agent
        for fn in lambda_functions:
            role.add_to_policy(
                iam.PolicyStatement(
                    actions=["lambda:InvokeFunction"],
                    resources=[fn.function_arn],
                )
            )
        return role

    # -----------------------------------------------------------------------
    # Task 5.5: Bedrock Agent resources
    # -----------------------------------------------------------------------
    def _create_bedrock_agents(
        self,
        *,
        foundation_model: str,
        assessment_lambda: _lambda.Function,
        execution_lambda: _lambda.Function,
        cluster_lock_lambda: _lambda.Function,
        assessment_agent_role: iam.Role,
        architecture_agent_role: iam.Role,
        execution_agent_role: iam.Role,
        orchestrator_agent_role: iam.Role,
    ) -> dict:
        """Create all four Bedrock Agents with action groups and aliases."""

        # Load OpenAPI schemas
        assessment_schema = self._load_schema("assessment-tools-openapi.json")
        execution_schema = self._load_schema("execution-tools-openapi.json")
        cluster_lock_schema = self._load_schema("cluster-lock-openapi.json")
        list_clusters_schema = self._load_schema("list-clusters-openapi.json")

        # --- Assessment Agent ---
        assessment_agent = cdk.aws_bedrock.CfnAgent(
            self,
            "AssessmentAgent",
            agent_name="redshift-assessment-agent",
            agent_resource_role_arn=assessment_agent_role.role_arn,
            foundation_model=foundation_model,
            instruction=ASSESSMENT_SYSTEM_PROMPT,
            auto_prepare=True,
            action_groups=[
                cdk.aws_bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="assessment-tools",
                    action_group_executor=cdk.aws_bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=assessment_lambda.function_arn,
                    ),
                    api_schema=cdk.aws_bedrock.CfnAgent.APISchemaProperty(
                        payload=assessment_schema,
                    ),
                ),
            ],
        )

        assessment_alias = cdk.aws_bedrock.CfnAgentAlias(
            self,
            "AssessmentAgentAlias",
            agent_id=assessment_agent.attr_agent_id,
            agent_alias_name="live",
        )

        # --- Architecture Agent ---
        architecture_agent = cdk.aws_bedrock.CfnAgent(
            self,
            "ArchitectureAgent",
            agent_name="redshift-architecture-agent",
            agent_resource_role_arn=architecture_agent_role.role_arn,
            foundation_model=foundation_model,
            instruction=ARCHITECTURE_SYSTEM_PROMPT,
            auto_prepare=True,
            action_groups=[
                cdk.aws_bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="assessment-tools",
                    action_group_executor=cdk.aws_bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=assessment_lambda.function_arn,
                    ),
                    api_schema=cdk.aws_bedrock.CfnAgent.APISchemaProperty(
                        payload=assessment_schema,
                    ),
                ),
                cdk.aws_bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="execution-tools",
                    action_group_executor=cdk.aws_bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=execution_lambda.function_arn,
                    ),
                    api_schema=cdk.aws_bedrock.CfnAgent.APISchemaProperty(
                        payload=execution_schema,
                    ),
                ),
            ],
        )

        architecture_alias = cdk.aws_bedrock.CfnAgentAlias(
            self,
            "ArchitectureAgentAlias",
            agent_id=architecture_agent.attr_agent_id,
            agent_alias_name="live",
        )

        # --- Execution Agent ---
        execution_agent = cdk.aws_bedrock.CfnAgent(
            self,
            "ExecutionAgent",
            agent_name="redshift-execution-agent",
            agent_resource_role_arn=execution_agent_role.role_arn,
            foundation_model=foundation_model,
            instruction=EXECUTION_SYSTEM_PROMPT,
            auto_prepare=True,
            action_groups=[
                cdk.aws_bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="execution-tools",
                    action_group_executor=cdk.aws_bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=execution_lambda.function_arn,
                    ),
                    api_schema=cdk.aws_bedrock.CfnAgent.APISchemaProperty(
                        payload=execution_schema,
                    ),
                ),
            ],
        )

        execution_alias = cdk.aws_bedrock.CfnAgentAlias(
            self,
            "ExecutionAgentAlias",
            agent_id=execution_agent.attr_agent_id,
            agent_alias_name="live",
        )

        # --- Orchestrator (Supervisor) Agent ---
        # The orchestrator role needs permission to invoke sub-agent aliases
        orchestrator_agent_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeAgent",
                    "bedrock:GetAgentAlias",
                    "bedrock:GetAgent",
                ],
                resources=["*"],
            )
        )

        # Collaborators are defined inline on the agent via agent_collaborators
        orchestrator_agent = cdk.aws_bedrock.CfnAgent(
            self,
            "OrchestratorAgent",
            agent_name="redshift-orchestrator-agent",
            agent_resource_role_arn=orchestrator_agent_role.role_arn,
            foundation_model=foundation_model,
            instruction=ORCHESTRATOR_SYSTEM_PROMPT,
            auto_prepare=True,
            action_groups=[
                cdk.aws_bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="cluster-lock",
                    action_group_executor=cdk.aws_bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=cluster_lock_lambda.function_arn,
                    ),
                    api_schema=cdk.aws_bedrock.CfnAgent.APISchemaProperty(
                        payload=cluster_lock_schema,
                    ),
                ),
                cdk.aws_bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="list-clusters",
                    action_group_executor=cdk.aws_bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=assessment_lambda.function_arn,
                    ),
                    api_schema=cdk.aws_bedrock.CfnAgent.APISchemaProperty(
                        payload=list_clusters_schema,
                    ),
                ),
            ],
            agent_collaboration="SUPERVISOR",
            agent_collaborators=[
                cdk.aws_bedrock.CfnAgent.AgentCollaboratorProperty(
                    agent_descriptor=cdk.aws_bedrock.CfnAgent.AgentDescriptorProperty(
                        alias_arn=assessment_alias.attr_agent_alias_arn,
                    ),
                    collaboration_instruction=(
                        "Delegate cluster analysis tasks including listing "
                        "clusters, analyzing configuration, retrieving "
                        "CloudWatch metrics, and WLM queue analysis to this "
                        "agent."
                    ),
                    collaborator_name="AssessmentAgent",
                    relay_conversation_history="TO_COLLABORATOR",
                ),
                cdk.aws_bedrock.CfnAgent.AgentCollaboratorProperty(
                    agent_descriptor=cdk.aws_bedrock.CfnAgent.AgentDescriptorProperty(
                        alias_arn=architecture_alias.attr_agent_alias_arn,
                    ),
                    collaboration_instruction=(
                        "Delegate workgroup architecture design tasks "
                        "including WLM-to-workgroup mapping, RPU sizing, "
                        "architecture pattern selection, and cost estimation "
                        "to this agent."
                    ),
                    collaborator_name="ArchitectureAgent",
                    relay_conversation_history="TO_COLLABORATOR",
                ),
                cdk.aws_bedrock.CfnAgent.AgentCollaboratorProperty(
                    agent_descriptor=cdk.aws_bedrock.CfnAgent.AgentDescriptorProperty(
                        alias_arn=execution_alias.attr_agent_alias_arn,
                    ),
                    collaboration_instruction=(
                        "Delegate migration execution tasks including "
                        "creating Serverless resources, restoring snapshots, "
                        "setting up data sharing, validating performance, "
                        "and planning cutover to this agent."
                    ),
                    collaborator_name="ExecutionAgent",
                    relay_conversation_history="TO_COLLABORATOR",
                ),
            ],
        )

        # Ensure orchestrator is created AFTER all sub-agent aliases are ready
        orchestrator_agent.add_dependency(assessment_alias)
        orchestrator_agent.add_dependency(architecture_alias)
        orchestrator_agent.add_dependency(execution_alias)

        orchestrator_alias = cdk.aws_bedrock.CfnAgentAlias(
            self,
            "OrchestratorAlias",
            agent_id=orchestrator_agent.attr_agent_id,
            agent_alias_name="live",
        )

        return {
            "orchestrator": orchestrator_agent,
            "orchestrator_alias": orchestrator_alias,
            "assessment": assessment_agent,
            "assessment_alias": assessment_alias,
            "architecture": architecture_agent,
            "architecture_alias": architecture_alias,
            "execution": execution_agent,
            "execution_alias": execution_alias,
        }

    def _load_schema(self, filename: str) -> str:
        """Load an OpenAPI schema JSON file as a string."""
        schema_path = _SCHEMAS_DIR / filename
        return schema_path.read_text(encoding="utf-8")

    # -----------------------------------------------------------------------
    # Task 5.7 + 5.8: Cognito resources and IAM roles for groups
    # -----------------------------------------------------------------------
    def _create_cognito_resources(
        self,
        *,
        lock_table: dynamodb.Table,
        orchestrator_agent_id: str,
    ) -> dict:
        """Create Cognito User Pool, App Client, Identity Pool, and groups."""

        # --- User Pool ---
        user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name="redshift-modernization-users",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_uppercase=True,
                require_lowercase=True,
                require_digits=True,
                require_symbols=True,
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )

        # --- App Client (public, no secret) ---
        app_client = user_pool.add_client(
            "AppClient",
            user_pool_client_name="redshift-modernization-ui",
            generate_secret=False,
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
            ),
        )

        # --- Identity Pool (L1 CfnIdentityPool) ---
        identity_pool = cognito.CfnIdentityPool(
            self,
            "IdentityPool",
            identity_pool_name="redshift_modernization_identity_pool",
            allow_unauthenticated_identities=False,
            cognito_identity_providers=[
                cognito.CfnIdentityPool.CognitoIdentityProviderProperty(
                    client_id=app_client.user_pool_client_id,
                    provider_name=user_pool.user_pool_provider_name,
                )
            ],
        )

        # --- IAM roles for Cognito groups ---
        admin_role = self._create_cognito_group_role(
            "RedshiftAdminRole",
            identity_pool_ref=identity_pool.ref,
            statements=[
                # Full Redshift access
                iam.PolicyStatement(
                    actions=[
                        "redshift:*",
                        "redshift-serverless:*",
                        "redshift-data:*",
                    ],
                    resources=["*"],
                ),
                # CloudWatch read
                iam.PolicyStatement(
                    actions=[
                        "cloudwatch:GetMetricStatistics",
                        "cloudwatch:ListMetrics",
                        "cloudwatch:GetMetricData",
                    ],
                    resources=["*"],
                ),
                # DynamoDB lock table
                iam.PolicyStatement(
                    actions=[
                        "dynamodb:PutItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:GetItem",
                    ],
                    resources=[lock_table.table_arn],
                ),
                # Bedrock InvokeAgent
                iam.PolicyStatement(
                    actions=["bedrock:InvokeAgent"],
                    resources=["*"],
                ),
            ],
        )

        viewer_role = self._create_cognito_group_role(
            "RedshiftViewerRole",
            identity_pool_ref=identity_pool.ref,
            statements=[
                # Read-only Redshift
                iam.PolicyStatement(
                    actions=["redshift:Describe*"],
                    resources=["*"],
                ),
                # Redshift Data API read
                iam.PolicyStatement(
                    actions=[
                        "redshift-data:ExecuteStatement",
                        "redshift-data:DescribeStatement",
                        "redshift-data:GetStatementResult",
                    ],
                    resources=["*"],
                ),
                # CloudWatch read
                iam.PolicyStatement(
                    actions=[
                        "cloudwatch:GetMetricStatistics",
                        "cloudwatch:ListMetrics",
                        "cloudwatch:GetMetricData",
                    ],
                    resources=["*"],
                ),
                # Bedrock InvokeAgent
                iam.PolicyStatement(
                    actions=["bedrock:InvokeAgent"],
                    resources=["*"],
                ),
            ],
        )

        # --- Cognito Groups ---
        cognito.CfnUserPoolGroup(
            self,
            "AdminGroup",
            user_pool_id=user_pool.user_pool_id,
            group_name="redshift-admin",
            description="Full access to all Redshift modernization operations",
            role_arn=admin_role.role_arn,
        )

        cognito.CfnUserPoolGroup(
            self,
            "ViewerGroup",
            user_pool_id=user_pool.user_pool_id,
            group_name="redshift-viewer",
            description="Read-only access to Redshift assessment operations",
            role_arn=viewer_role.role_arn,
        )

        # --- Identity Pool role attachment ---
        cognito.CfnIdentityPoolRoleAttachment(
            self,
            "IdentityPoolRoles",
            identity_pool_id=identity_pool.ref,
            roles={
                "authenticated": admin_role.role_arn,
            },
            role_mappings={
                "cognito": cognito.CfnIdentityPoolRoleAttachment.RoleMappingProperty(
                    type="Token",
                    ambiguous_role_resolution="AuthenticatedRole",
                    identity_provider=f"{user_pool.user_pool_provider_name}:{app_client.user_pool_client_id}",
                ),
            },
        )

        return {
            "user_pool": user_pool,
            "app_client": app_client,
            "identity_pool": identity_pool,
            "admin_role": admin_role,
            "viewer_role": viewer_role,
        }

    def _create_cognito_group_role(
        self,
        role_id: str,
        *,
        identity_pool_ref: str,
        statements: list[iam.PolicyStatement],
    ) -> iam.Role:
        """Create an IAM role for a Cognito group with Identity Pool trust."""
        role = iam.Role(
            self,
            role_id,
            assumed_by=iam.FederatedPrincipal(
                "cognito-identity.amazonaws.com",
                conditions={
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": identity_pool_ref,
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "authenticated",
                    },
                },
                assume_role_action="sts:AssumeRoleWithWebIdentity",
            ),
        )
        for stmt in statements:
            role.add_to_policy(stmt)
        return role

    # -----------------------------------------------------------------------
    # Task 5.9: CloudFormation outputs
    # -----------------------------------------------------------------------
    def _create_outputs(self, agents: dict, cognito_resources: dict) -> None:
        """Create CloudFormation outputs for UI configuration."""
        CfnOutput(
            self,
            "OrchestratorAgentId",
            value=agents["orchestrator"].attr_agent_id,
            description="Bedrock Orchestrator Agent ID",
        )
        CfnOutput(
            self,
            "OrchestratorAliasId",
            value=agents["orchestrator_alias"].attr_agent_alias_id,
            description="Bedrock Orchestrator Agent Alias ID",
        )
        CfnOutput(
            self,
            "CognitoUserPoolId",
            value=cognito_resources["user_pool"].user_pool_id,
            description="Cognito User Pool ID",
        )
        CfnOutput(
            self,
            "CognitoAppClientId",
            value=cognito_resources["app_client"].user_pool_client_id,
            description="Cognito App Client ID",
        )
        CfnOutput(
            self,
            "CognitoIdentityPoolId",
            value=cognito_resources["identity_pool"].ref,
            description="Cognito Identity Pool ID",
        )
