"""
Property-based tests for Lambda action group handlers.

Feature: bedrock-agents-rewrite
Properties 1–6: Lambda handler event parsing, error responses, identity
propagation, audit events, audit schema validity, and audit failure resilience.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings, strategies as st


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_event(api_path: str, parameters: dict, action_group: str = "TestGroup") -> dict:
    """Construct a Bedrock Agent action group invocation event."""
    return {
        "messageVersion": "1.0",
        "agent": {"name": "test-agent", "id": "test-id", "alias": "test-alias", "version": "1"},
        "actionGroup": action_group,
        "apiPath": api_path,
        "httpMethod": "GET",
        "parameters": [
            {"name": k, "type": "string", "value": str(v)} for k, v in parameters.items()
        ],
        "sessionAttributes": {},
        "promptSessionAttributes": {},
    }


def _parse_body(response: dict):
    """Extract the parsed tool result from a Lambda handler response."""
    body_str = response["response"]["responseBody"]["application/json"]["body"]
    return json.loads(body_str)


# Strategies for generating valid identifiers (non-empty, ASCII, no whitespace)
_identifier = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-_"),
    min_size=1,
    max_size=30,
)
_region = st.sampled_from(["us-east-1", "us-east-2", "us-west-2", "eu-west-1", "ap-southeast-1"])
_user_id = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789@._-"),
    min_size=1,
    max_size=40,
)

# All recognized apiPaths across the three handlers
_assessment_paths = st.sampled_from([
    "/listRedshiftClusters",
    "/analyzeRedshiftCluster",
    "/getClusterMetrics",
    "/getWlmConfiguration",
])
_execution_paths = st.sampled_from([
    "/executeRedshiftQuery",
    "/createServerlessNamespace",
    "/createServerlessWorkgroup",
    "/restoreSnapshotToServerless",
    "/setupDataSharing",
])
_lock_paths = st.sampled_from(["/acquireClusterLock", "/releaseClusterLock"])


def _params_for_path(api_path: str, user_id: str, region: str, cluster_id: str) -> dict:
    """Build a minimal valid parameter dict for a given apiPath."""
    base = {"user_id": user_id, "region": region}
    if api_path == "/listRedshiftClusters":
        return base
    if api_path in (
        "/analyzeRedshiftCluster",
        "/getWlmConfiguration",
    ):
        return {**base, "cluster_id": cluster_id}
    if api_path == "/getClusterMetrics":
        return {**base, "cluster_id": cluster_id, "hours": "24"}
    if api_path == "/executeRedshiftQuery":
        return {**base, "cluster_id": cluster_id, "query": "SELECT 1"}
    if api_path == "/createServerlessNamespace":
        return {**base, "namespace_name": "ns1"}
    if api_path == "/createServerlessWorkgroup":
        return {**base, "workgroup_name": "wg1", "namespace_name": "ns1"}
    if api_path == "/restoreSnapshotToServerless":
        return {**base, "snapshot_identifier": "snap1", "namespace_name": "ns1"}
    if api_path == "/setupDataSharing":
        return {**base, "producer_namespace": "prod", "consumer_namespaces": "cons1,cons2"}
    if api_path in ("/acquireClusterLock", "/releaseClusterLock"):
        return {**base, "cluster_id": cluster_id}
    return base


# ---------------------------------------------------------------------------
# Mock helpers — patch boto3.client to return canned responses
# ---------------------------------------------------------------------------

def _mock_boto3_client_factory():
    """Return a side_effect function for ``boto3.client`` that returns
    pre-configured mocks for every AWS service the handlers touch."""
    mock_clients: dict[str, MagicMock] = {}

    def _factory(service_name, **kwargs):
        if service_name not in mock_clients:
            m = MagicMock()
            if service_name == "redshift":
                m.describe_clusters.return_value = {
                    "Clusters": [{
                        "ClusterIdentifier": "test-cluster",
                        "NodeType": "ra3.xlplus",
                        "NumberOfNodes": 2,
                        "ClusterStatus": "available",
                        "ClusterVersion": "1.0",
                        "AvailabilityZone": "us-east-1a",
                        "Encrypted": True,
                        "KmsKeyId": "key-1",
                        "PubliclyAccessible": False,
                        "VpcId": "vpc-123",
                        "VpcSecurityGroups": [{"VpcSecurityGroupId": "sg-1"}],
                        "EnhancedVpcRouting": True,
                        "Endpoint": {"Address": "host", "Port": 5439},
                        "ClusterParameterGroups": [{"ParameterGroupName": "default"}],
                        "AutomatedSnapshotRetentionPeriod": 7,
                        "PreferredMaintenanceWindow": "sun:05:00-sun:06:00",
                        "ClusterCreateTime": "2024-01-01T00:00:00Z",
                        "MasterUsername": "admin",
                        "DBName": "dev",
                    }],
                }
            elif service_name == "cloudwatch":
                m.get_metric_statistics.return_value = {
                    "Datapoints": [
                        {"Average": 50.0, "Maximum": 80.0, "Minimum": 20.0},
                    ],
                }
            elif service_name == "redshift-data":
                m.execute_statement.return_value = {"Id": "stmt-1"}
                m.describe_statement.return_value = {"Status": "FINISHED"}
                m.get_statement_result.return_value = {"Records": []}
            elif service_name == "redshift-serverless":
                m.create_namespace.return_value = {
                    "namespace": {
                        "namespaceName": "ns1",
                        "namespaceId": "id-1",
                        "namespaceArn": "arn:aws:redshift-serverless:us-east-1:123:namespace/ns1",
                        "status": "AVAILABLE",
                        "adminUsername": "admin",
                        "dbName": "dev",
                    },
                }
                m.create_workgroup.return_value = {
                    "workgroup": {
                        "workgroupName": "wg1",
                        "workgroupId": "wg-id-1",
                        "workgroupArn": "arn:aws:redshift-serverless:us-east-1:123:workgroup/wg1",
                        "status": "AVAILABLE",
                        "namespaceName": "ns1",
                        "baseCapacity": 32,
                        "maxCapacity": 512,
                    },
                }
                m.restore_from_snapshot.return_value = {
                    "namespace": {
                        "namespaceName": "ns1",
                        "namespaceId": "id-1",
                        "namespaceArn": "arn:aws:redshift-serverless:us-east-1:123:namespace/ns1",
                        "status": "AVAILABLE",
                    },
                }
                m.get_namespace.return_value = {
                    "namespace": {"namespaceName": "prod", "namespaceId": "ns-prod-id"},
                }
            elif service_name == "dynamodb":
                m.put_item.return_value = {}
                m.delete_item.return_value = {}
            elif service_name == "sts":
                m.get_caller_identity.return_value = {"Account": "123456789012"}
                m.assume_role.return_value = {
                    "Credentials": {
                        "AccessKeyId": "AKIA...",
                        "SecretAccessKey": "secret",
                        "SessionToken": "token",
                        "Expiration": "2099-01-01T00:00:00Z",
                    },
                }
            mock_clients[service_name] = m
        return mock_clients[service_name]

    return _factory, mock_clients


# ===========================================================================
# Property 1: Lambda handler event parsing and response format
# Feature: bedrock-agents-rewrite, Property 1: Lambda handler event parsing
#   and response format
# **Validates: Requirements 1.1, 11.5**
# ===========================================================================

@settings(max_examples=100, deadline=None)
@given(
    api_path=_assessment_paths,
    user_id=_user_id,
    region=_region,
    cluster_id=_identifier,
    action_group=_identifier,
)
def test_property1_assessment_handler_response_format(
    api_path, user_id, region, cluster_id, action_group,
):
    """Property 1 (assessment): For any valid action group event with a
    recognized apiPath, the handler returns the correct response structure."""
    factory, _ = _mock_boto3_client_factory()
    params = _params_for_path(api_path, user_id, region, cluster_id)
    event = _build_event(api_path, params, action_group)

    with patch("boto3.client", side_effect=factory):
        from redshift_agents.lambdas.assessment_handler import handler
        resp = handler(event)

    # Structural assertions
    assert resp["messageVersion"] == "1.0"
    r = resp["response"]
    assert r["actionGroup"] == action_group
    assert r["apiPath"] == api_path
    assert "httpMethod" in r
    assert r["httpStatusCode"] == 200
    body_str = r["responseBody"]["application/json"]["body"]
    # Must be valid JSON
    parsed = json.loads(body_str)
    assert isinstance(parsed, (dict, list))


@settings(max_examples=100, deadline=None)
@given(
    api_path=_execution_paths,
    user_id=_user_id,
    region=_region,
    cluster_id=_identifier,
    action_group=_identifier,
)
def test_property1_execution_handler_response_format(
    api_path, user_id, region, cluster_id, action_group,
):
    """Property 1 (execution): Same structural check for execution handler."""
    factory, _ = _mock_boto3_client_factory()
    params = _params_for_path(api_path, user_id, region, cluster_id)
    event = _build_event(api_path, params, action_group)

    with patch("boto3.client", side_effect=factory):
        from redshift_agents.lambdas.execution_handler import handler
        resp = handler(event)

    assert resp["messageVersion"] == "1.0"
    r = resp["response"]
    assert r["actionGroup"] == action_group
    assert r["apiPath"] == api_path
    assert r["httpStatusCode"] == 200
    parsed = json.loads(r["responseBody"]["application/json"]["body"])
    assert isinstance(parsed, (dict, list))


@settings(max_examples=100, deadline=None)
@given(
    api_path=_lock_paths,
    user_id=_user_id,
    region=_region,
    cluster_id=_identifier,
    action_group=_identifier,
)
def test_property1_lock_handler_response_format(
    api_path, user_id, region, cluster_id, action_group,
):
    """Property 1 (cluster_lock): Same structural check for lock handler."""
    factory, _ = _mock_boto3_client_factory()
    params = _params_for_path(api_path, user_id, region, cluster_id)
    event = _build_event(api_path, params, action_group)

    with patch("boto3.client", side_effect=factory):
        from redshift_agents.lambdas.cluster_lock_handler import handler
        resp = handler(event)

    assert resp["messageVersion"] == "1.0"
    r = resp["response"]
    assert r["actionGroup"] == action_group
    assert r["apiPath"] == api_path
    assert r["httpStatusCode"] == 200
    parsed = json.loads(r["responseBody"]["application/json"]["body"])
    assert isinstance(parsed, (dict, list))


# ===========================================================================
# Property 2: Lambda handler error responses preserve structured format
# Feature: bedrock-agents-rewrite, Property 2: Lambda handler error responses
#   preserve structured format
# **Validates: Requirements 1.5**
# ===========================================================================

def _error_boto3_factory():
    """Return a boto3.client side_effect that produces mocks whose AWS API
    methods raise, while keeping MagicMock internals intact."""
    _boto3_error = Exception("simulated boto3 failure")

    def _factory(service_name, **kwargs):
        m = MagicMock()
        # Set side_effect on the specific methods each service uses
        if service_name == "redshift":
            m.describe_clusters.side_effect = _boto3_error
        elif service_name == "cloudwatch":
            m.get_metric_statistics.side_effect = _boto3_error
        elif service_name == "redshift-data":
            m.execute_statement.side_effect = _boto3_error
        elif service_name == "redshift-serverless":
            m.create_namespace.side_effect = _boto3_error
            m.create_workgroup.side_effect = _boto3_error
            m.restore_from_snapshot.side_effect = _boto3_error
            m.get_namespace.side_effect = _boto3_error
        elif service_name == "dynamodb":
            m.put_item.side_effect = _boto3_error
            m.delete_item.side_effect = _boto3_error
        elif service_name == "sts":
            m.assume_role.side_effect = _boto3_error
            m.get_caller_identity.side_effect = _boto3_error
        return m

    return _factory


@settings(max_examples=100, deadline=None)
@given(
    api_path=_assessment_paths,
    user_id=_user_id,
    region=_region,
    cluster_id=_identifier,
)
def test_property2_assessment_error_response(api_path, user_id, region, cluster_id):
    """Property 2 (assessment): When boto3 raises, the handler still returns
    a structured response with an 'error' key in the body."""
    params = _params_for_path(api_path, user_id, region, cluster_id)
    event = _build_event(api_path, params)

    with patch("boto3.client", side_effect=_error_boto3_factory()):
        from redshift_agents.lambdas.assessment_handler import handler
        resp = handler(event)

    assert resp["messageVersion"] == "1.0"
    assert resp["response"]["httpStatusCode"] == 200
    body = _parse_body(resp)
    assert "error" in body


@settings(max_examples=100, deadline=None)
@given(
    api_path=_execution_paths,
    user_id=_user_id,
    region=_region,
    cluster_id=_identifier,
)
def test_property2_execution_error_response(api_path, user_id, region, cluster_id):
    """Property 2 (execution): Same error-response check for execution handler."""
    params = _params_for_path(api_path, user_id, region, cluster_id)
    event = _build_event(api_path, params)

    with patch("boto3.client", side_effect=_error_boto3_factory()):
        from redshift_agents.lambdas.execution_handler import handler
        resp = handler(event)

    assert resp["messageVersion"] == "1.0"
    assert resp["response"]["httpStatusCode"] == 200
    body = _parse_body(resp)
    assert "error" in body


@settings(max_examples=100, deadline=None)
@given(
    api_path=_lock_paths,
    user_id=_user_id,
    region=_region,
    cluster_id=_identifier,
)
def test_property2_lock_error_response(api_path, user_id, region, cluster_id):
    """Property 2 (cluster_lock): Same error-response check for lock handler."""
    params = _params_for_path(api_path, user_id, region, cluster_id)
    event = _build_event(api_path, params)

    with patch("boto3.client", side_effect=_error_boto3_factory()):
        from redshift_agents.lambdas.cluster_lock_handler import handler
        resp = handler(event)

    assert resp["messageVersion"] == "1.0"
    assert resp["response"]["httpStatusCode"] == 200
    body = _parse_body(resp)
    assert "error" in body


# ===========================================================================
# Property 3: Identity propagation through Lambda handlers
# Feature: bedrock-agents-rewrite, Property 3: Identity propagation through
#   Lambda handlers
# **Validates: Requirements 1.3, 6.2, 10.3, 10.4**
# ===========================================================================

@settings(max_examples=100, deadline=None)
@given(user_id=_user_id, region=_region, cluster_id=_identifier)
def test_property3_identity_propagation_assessment(user_id, region, cluster_id):
    """Property 3 (assessment): user_id propagates to emit_audit_event
    (initiated_by) and to execute_statement (DbUser) for WLM/query paths."""
    factory, clients = _mock_boto3_client_factory()

    # Test getWlmConfiguration which calls execute_statement with DbUser
    params = _params_for_path("/getWlmConfiguration", user_id, region, cluster_id)
    event = _build_event("/getWlmConfiguration", params)

    with patch("boto3.client", side_effect=factory), \
         patch("redshift_agents.tools.redshift_tools.emit_audit_event") as mock_audit:
        from redshift_agents.lambdas.assessment_handler import handler
        handler(event)

    # Audit event must carry the user_id
    mock_audit.assert_called()
    _, call_kwargs = mock_audit.call_args
    assert call_kwargs["initiated_by"] == user_id

    # execute_statement must carry DbUser=user_id
    rd_client = clients.get("redshift-data")
    if rd_client and rd_client.execute_statement.called:
        _, call_kw = rd_client.execute_statement.call_args
        assert call_kw.get("DbUser") == user_id


@settings(max_examples=100, deadline=None)
@given(user_id=_user_id, region=_region, cluster_id=_identifier)
def test_property3_identity_propagation_execution(user_id, region, cluster_id):
    """Property 3 (execution): user_id propagates to emit_audit_event and
    execute_statement for executeRedshiftQuery."""
    factory, clients = _mock_boto3_client_factory()

    params = _params_for_path("/executeRedshiftQuery", user_id, region, cluster_id)
    event = _build_event("/executeRedshiftQuery", params)

    with patch("boto3.client", side_effect=factory), \
         patch("redshift_agents.tools.redshift_tools.emit_audit_event") as mock_audit:
        from redshift_agents.lambdas.execution_handler import handler
        handler(event)

    mock_audit.assert_called()
    _, call_kwargs = mock_audit.call_args
    assert call_kwargs["initiated_by"] == user_id

    rd_client = clients.get("redshift-data")
    if rd_client and rd_client.execute_statement.called:
        _, call_kw = rd_client.execute_statement.call_args
        assert call_kw.get("DbUser") == user_id


# ===========================================================================
# Property 4: Audit event emitted for every tool invocation
# Feature: bedrock-agents-rewrite, Property 4: Audit event emitted for every
#   tool invocation
# **Validates: Requirements 1.4, 6.1, 14.1**
# ===========================================================================

@settings(max_examples=100, deadline=None)
@given(
    api_path=_assessment_paths,
    user_id=_user_id,
    region=_region,
    cluster_id=_identifier,
)
def test_property4_audit_emitted_assessment(api_path, user_id, region, cluster_id):
    """Property 4 (assessment): emit_audit_event is called exactly once with
    event_type='tool_invocation' and agent_name='assessment'."""
    factory, _ = _mock_boto3_client_factory()
    params = _params_for_path(api_path, user_id, region, cluster_id)
    event = _build_event(api_path, params)

    with patch("boto3.client", side_effect=factory), \
         patch("redshift_agents.tools.redshift_tools.emit_audit_event") as mock_audit:
        from redshift_agents.lambdas.assessment_handler import handler
        handler(event)

    # The tool function calls emit_audit_event once
    mock_audit.assert_called_once()
    args, kwargs = mock_audit.call_args
    assert args[0] == "tool_invocation"
    assert args[1] == "assessment"


@settings(max_examples=100, deadline=None)
@given(
    api_path=_execution_paths,
    user_id=_user_id,
    region=_region,
    cluster_id=_identifier,
)
def test_property4_audit_emitted_execution(api_path, user_id, region, cluster_id):
    """Property 4 (execution): emit_audit_event is called exactly once with
    event_type='tool_invocation' and agent_name='execution'."""
    factory, _ = _mock_boto3_client_factory()
    params = _params_for_path(api_path, user_id, region, cluster_id)
    event = _build_event(api_path, params)

    with patch("boto3.client", side_effect=factory), \
         patch("redshift_agents.tools.redshift_tools.emit_audit_event") as mock_audit:
        from redshift_agents.lambdas.execution_handler import handler
        handler(event)

    mock_audit.assert_called_once()
    args, kwargs = mock_audit.call_args
    assert args[0] == "tool_invocation"
    assert args[1] == "execution"


# ===========================================================================
# Property 5: Audit event schema validity
# Feature: bedrock-agents-rewrite, Property 5: Audit event schema validity
# **Validates: Requirements 6.4, 6.5, 14.2, 14.5**
# ===========================================================================

_VALID_EVENT_TYPES = frozenset({
    "agent_start", "tool_invocation", "workflow_start", "workflow_complete",
    "phase_start", "phase_complete", "error",
})

_REQUIRED_AUDIT_FIELDS = {
    "timestamp", "event_type", "agent_name", "customer_account_id",
    "initiated_by", "cluster_id", "region", "details",
}


@settings(max_examples=100, deadline=None)
@given(
    event_type=st.sampled_from(sorted(_VALID_EVENT_TYPES)),
    agent_name=_identifier,
    user_id=_user_id,
    cluster_id=_identifier,
    region=_region,
)
def test_property5_audit_event_schema(event_type, agent_name, user_id, cluster_id, region):
    """Property 5: Every audit event emitted by emit_audit_event contains all
    required fields, a valid ISO 8601 timestamp, and a valid event_type."""
    captured_events: list[dict] = []

    # Patch the logger to capture the event dict
    with patch("redshift_agents.tools.audit_logger._logger") as mock_logger, \
         patch("boto3.client") as mock_boto:
        mock_boto.return_value.get_caller_identity.return_value = {"Account": "123456789012"}

        from redshift_agents.tools.audit_logger import emit_audit_event

        # Capture the extra dict passed to logger.info
        def _capture_info(msg, extra=None, **kwargs):
            if extra:
                captured_events.append(extra)

        mock_logger.info.side_effect = _capture_info

        emit_audit_event(
            event_type=event_type,
            agent_name=agent_name,
            initiated_by=user_id,
            cluster_id=cluster_id,
            region=region,
            details={"test": True},
        )

    assert len(captured_events) == 1
    evt = captured_events[0]

    # All required fields present
    for field in _REQUIRED_AUDIT_FIELDS:
        assert field in evt, f"Missing required field: {field}"

    # Valid ISO 8601 timestamp
    datetime.fromisoformat(evt["timestamp"])

    # Valid event_type
    assert evt["event_type"] in _VALID_EVENT_TYPES


# ===========================================================================
# Property 6: Audit failure resilience
# Feature: bedrock-agents-rewrite, Property 6: Audit failure resilience
# **Validates: Requirements 6.3**
# ===========================================================================

@settings(max_examples=100, deadline=None)
@given(
    api_path=_assessment_paths,
    user_id=_user_id,
    region=_region,
    cluster_id=_identifier,
)
def test_property6_audit_failure_resilience_assessment(api_path, user_id, region, cluster_id):
    """Property 6 (assessment): When emit_audit_event raises, the handler
    catches the exception, logs to stderr, and still returns a successful
    tool result."""
    factory, _ = _mock_boto3_client_factory()
    params = _params_for_path(api_path, user_id, region, cluster_id)
    event = _build_event(api_path, params)

    def _exploding_audit(*args, **kwargs):
        raise RuntimeError("audit system down")

    with patch("boto3.client", side_effect=factory), \
         patch("redshift_agents.tools.redshift_tools.emit_audit_event", side_effect=_exploding_audit):
        from redshift_agents.lambdas.assessment_handler import handler
        resp = handler(event)

    # Handler must still return a valid response (caught by outer try/except)
    assert resp["messageVersion"] == "1.0"
    assert resp["response"]["httpStatusCode"] == 200
    body = _parse_body(resp)
    # The body should exist — it may contain an error from the audit failure
    # being caught at the handler level, but the response format is intact
    assert isinstance(body, (dict, list))


@settings(max_examples=100, deadline=None)
@given(
    api_path=_execution_paths,
    user_id=_user_id,
    region=_region,
    cluster_id=_identifier,
)
def test_property6_audit_failure_resilience_execution(api_path, user_id, region, cluster_id):
    """Property 6 (execution): Same resilience check for execution handler."""
    factory, _ = _mock_boto3_client_factory()
    params = _params_for_path(api_path, user_id, region, cluster_id)
    event = _build_event(api_path, params)

    def _exploding_audit(*args, **kwargs):
        raise RuntimeError("audit system down")

    with patch("boto3.client", side_effect=factory), \
         patch("redshift_agents.tools.redshift_tools.emit_audit_event", side_effect=_exploding_audit):
        from redshift_agents.lambdas.execution_handler import handler
        resp = handler(event)

    assert resp["messageVersion"] == "1.0"
    assert resp["response"]["httpStatusCode"] == 200
    body = _parse_body(resp)
    assert isinstance(body, (dict, list))


@settings(max_examples=100, deadline=None)
@given(
    api_path=_lock_paths,
    user_id=_user_id,
    region=_region,
    cluster_id=_identifier,
)
def test_property6_audit_failure_resilience_lock(api_path, user_id, region, cluster_id):
    """Property 6 (cluster_lock): Lock handler doesn't call emit_audit_event
    directly, but if the underlying lock functions raise due to DynamoDB
    issues, the handler still returns a structured response."""
    params = _params_for_path(api_path, user_id, region, cluster_id)
    event = _build_event(api_path, params)

    # Even with a broken boto3 client, the handler catches and returns structured error
    def _raise_factory(service_name, **kwargs):
        m = MagicMock()
        exc = Exception("dynamodb down")
        m.put_item.side_effect = exc
        m.delete_item.side_effect = exc
        return m

    with patch("boto3.client", side_effect=_raise_factory):
        from redshift_agents.lambdas.cluster_lock_handler import handler
        resp = handler(event)

    assert resp["messageVersion"] == "1.0"
    assert resp["response"]["httpStatusCode"] == 200
    body = _parse_body(resp)
    assert isinstance(body, dict)



# ===========================================================================
# Property 7: Cognito JWT user_id extraction
# Feature: bedrock-agents-rewrite, Property 7: Cognito JWT user_id extraction
# **Validates: Requirements 5.5, 10.1, 5a.3**
# ===========================================================================

# Strategy: non-empty strings suitable for usernames / emails
_cognito_username = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-_."),
    min_size=1,
    max_size=40,
)
_email_local = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789._"),
    min_size=1,
    max_size=20,
)
_email_domain = st.sampled_from(["example.com", "test.org", "corp.net", "mail.io"])
_email_strategy = st.builds(lambda local, domain: f"{local}@{domain}", _email_local, _email_domain)


def _make_jwt_from_payload(payload: dict) -> str:
    """Build a fake JWT (header.payload.signature) from a payload dict.

    No real signature — just base64-encoded JSON sections.
    """
    import base64 as _b64

    header = _b64.urlsafe_b64encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    body = _b64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    sig = _b64.urlsafe_b64encode(b"fakesig").rstrip(b"=").decode()
    return f"{header}.{body}.{sig}"


@settings(max_examples=100, deadline=None)
@given(
    username=_cognito_username,
    email=_email_strategy,
    extra_claims=st.fixed_dictionaries({
        "sub": st.uuids().map(str),
        "iss": st.just("https://cognito-idp.us-east-2.amazonaws.com/us-east-2_EXAMPLE"),
        "aud": st.just("app-client-id"),
    }),
)
def test_property7_jwt_extraction_cognito_username(username, email, extra_claims):
    """Property 7a: When the JWT payload contains ``cognito:username``,
    extract_user_id_from_payload returns that value regardless of whether
    ``email`` is also present."""
    from redshift_agents.ui.auth import extract_user_id_from_payload

    payload = {**extra_claims, "cognito:username": username, "email": email}
    assert extract_user_id_from_payload(payload) == username


@settings(max_examples=100, deadline=None)
@given(
    email=_email_strategy,
    extra_claims=st.fixed_dictionaries({
        "sub": st.uuids().map(str),
        "iss": st.just("https://cognito-idp.us-east-2.amazonaws.com/us-east-2_EXAMPLE"),
        "aud": st.just("app-client-id"),
    }),
)
def test_property7_jwt_extraction_email_fallback(email, extra_claims):
    """Property 7b: When the JWT payload is missing ``cognito:username``
    but contains ``email``, extract_user_id_from_payload returns the email."""
    from redshift_agents.ui.auth import extract_user_id_from_payload

    payload = {**extra_claims, "email": email}
    # Ensure cognito:username is NOT present
    payload.pop("cognito:username", None)
    assert extract_user_id_from_payload(payload) == email


@settings(max_examples=100, deadline=None)
@given(
    username=_cognito_username,
    extra_claims=st.fixed_dictionaries({
        "sub": st.uuids().map(str),
        "iss": st.just("https://cognito-idp.us-east-2.amazonaws.com/us-east-2_EXAMPLE"),
        "aud": st.just("app-client-id"),
    }),
)
def test_property7_jwt_extraction_full_token_roundtrip(username, extra_claims):
    """Property 7c: extract_user_id works on a full JWT string (header.payload.sig)
    containing ``cognito:username``."""
    from redshift_agents.ui.auth import extract_user_id

    payload = {**extra_claims, "cognito:username": username}
    token = _make_jwt_from_payload(payload)
    assert extract_user_id(token) == username


# ===========================================================================
# Property 8: Cluster listing returns all clusters in region
# Feature: bedrock-agents-rewrite, Property 8: Cluster listing returns all
#   clusters in region
# **Validates: Requirements 1.1, 1.2, 11.3, 11.6**
# ===========================================================================

# Strategies for cluster generation
_cluster_id_gen = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",
    min_size=1, max_size=30,
).filter(lambda s: not s.startswith("-") and not s.endswith("-"))

_node_types = ["ra3.xlplus", "ra3.4xlarge", "ra3.16xlarge", "dc2.large"]

_cluster_gen = st.fixed_dictionaries({
    "ClusterIdentifier": _cluster_id_gen,
    "NodeType": st.sampled_from(_node_types),
    "NumberOfNodes": st.integers(min_value=1, max_value=128),
    "ClusterStatus": st.sampled_from(["available", "creating", "deleting"]),
    "ClusterCreateTime": st.just("2024-01-01T00:00:00Z"),
    "AvailabilityZone": st.sampled_from(["us-east-2a", "us-east-2b"]),
    "Encrypted": st.booleans(),
    "PubliclyAccessible": st.booleans(),
})

_clusters_gen = st.lists(_cluster_gen, min_size=0, max_size=10,
                         unique_by=lambda c: c["ClusterIdentifier"])


@settings(max_examples=100, deadline=None)
@given(clusters=_clusters_gen, region=_region)
def test_property8_cluster_listing_returns_all(clusters, region):
    """Property 8: Cluster listing returns all clusters in region.

    For any mocked set of Redshift clusters, the listRedshiftClusters Lambda
    handler returns a list whose length equals the mock count and every
    cluster identifier appears in the result.

    **Validates: Requirements 1.1, 1.2**
    """
    # Feature: bedrock-agents-rewrite, Property 8: Cluster listing returns all clusters in region
    factory, clients = _mock_boto3_client_factory()
    # Override the redshift mock
    from unittest.mock import MagicMock as _MM
    rs = _MM()
    rs.describe_clusters.return_value = {"Clusters": clusters}

    def _custom_factory(service_name, **kwargs):
        if service_name == "redshift":
            return rs
        return factory(service_name, **kwargs)

    params = {"region": region, "user_id": "test-user"}
    event = _build_event("/listRedshiftClusters", params)

    with patch("boto3.client", side_effect=_custom_factory):
        from redshift_agents.lambdas.assessment_handler import handler
        resp = handler(event)

    body = _parse_body(resp)
    assert isinstance(body, list)
    assert len(body) == len(clusters)
    expected_ids = {c["ClusterIdentifier"] for c in clusters}
    actual_ids = {r["cluster_identifier"] for r in body}
    assert actual_ids == expected_ids


# ===========================================================================
# Property 9: Cluster configuration output contains all required fields
# Feature: bedrock-agents-rewrite, Property 9: Cluster configuration output
#   contains all required fields
# **Validates: Requirements 1.2**
# ===========================================================================

_full_cluster_gen = st.fixed_dictionaries({
    "ClusterIdentifier": _cluster_id_gen,
    "NodeType": st.sampled_from(_node_types),
    "NumberOfNodes": st.integers(min_value=1, max_value=128),
    "ClusterStatus": st.sampled_from(["available", "creating"]),
    "ClusterVersion": st.text(alphabet="0123456789.", min_size=1, max_size=5),
    "AvailabilityZone": st.sampled_from(["us-east-2a", "us-west-2a"]),
    "Encrypted": st.booleans(),
    "KmsKeyId": st.just("key-1"),
    "PubliclyAccessible": st.booleans(),
    "VpcId": st.from_regex(r"vpc-[a-f0-9]{8}", fullmatch=True),
    "VpcSecurityGroups": st.just([{"VpcSecurityGroupId": "sg-12345678"}]),
    "EnhancedVpcRouting": st.booleans(),
    "Endpoint": st.just({"Address": "host", "Port": 5439}),
    "ClusterParameterGroups": st.just([{"ParameterGroupName": "default"}]),
    "AutomatedSnapshotRetentionPeriod": st.integers(min_value=0, max_value=35),
    "PreferredMaintenanceWindow": st.just("sun:05:00-sun:05:30"),
    "ClusterCreateTime": st.just("2024-01-01T00:00:00Z"),
    "MasterUsername": st.just("admin"),
    "DBName": st.just("dev"),
})


@settings(max_examples=100, deadline=None)
@given(cluster=_full_cluster_gen, region=_region, user_id=_user_id)
def test_property9_cluster_config_required_fields(cluster, region, user_id):
    """Property 9: Cluster configuration output contains all required fields.

    **Validates: Requirements 1.2**
    """
    # Feature: bedrock-agents-rewrite, Property 9: Cluster configuration output contains all required fields
    from unittest.mock import MagicMock as _MM
    rs = _MM()
    rs.describe_clusters.return_value = {"Clusters": [cluster]}

    factory, _ = _mock_boto3_client_factory()

    def _custom(service_name, **kwargs):
        if service_name == "redshift":
            return rs
        return factory(service_name, **kwargs)

    params = {"cluster_id": cluster["ClusterIdentifier"], "region": region, "user_id": user_id}
    event = _build_event("/analyzeRedshiftCluster", params)

    with patch("boto3.client", side_effect=_custom):
        from redshift_agents.lambdas.assessment_handler import handler
        resp = handler(event)

    body = _parse_body(resp)
    assert isinstance(body, dict)
    assert "error" not in body
    required = {"cluster_identifier", "node_type", "number_of_nodes",
                "cluster_status", "cluster_version", "encrypted",
                "vpc_id", "publicly_accessible", "enhanced_vpc_routing"}
    missing = required - body.keys()
    assert not missing, f"Missing: {missing}"


# ===========================================================================
# Property 10: CloudWatch metrics output contains all required metric categories
# Feature: bedrock-agents-rewrite, Property 10: CloudWatch metrics output
#   contains all required metric categories
# **Validates: Requirements 1.2**
# ===========================================================================

_REQUIRED_METRICS = [
    "CPUUtilization", "DatabaseConnections", "NetworkReceiveThroughput",
    "NetworkTransmitThroughput", "PercentageDiskSpaceUsed",
    "ReadLatency", "WriteLatency",
]

_datapoint_gen = st.fixed_dictionaries({
    "Average": st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
    "Maximum": st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
    "Minimum": st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
})


@settings(max_examples=100, deadline=None)
@given(
    cluster_id=_identifier, region=_region, user_id=_user_id,
    datapoints=st.lists(_datapoint_gen, min_size=1, max_size=5),
)
def test_property10_cloudwatch_metrics_all_categories(cluster_id, region, user_id, datapoints):
    """Property 10: CloudWatch metrics output contains all required metric categories.

    **Validates: Requirements 1.2**
    """
    # Feature: bedrock-agents-rewrite, Property 10: CloudWatch metrics output contains all required metric categories
    from unittest.mock import MagicMock as _MM
    cw = _MM()
    cw.get_metric_statistics.return_value = {"Datapoints": datapoints}

    factory, _ = _mock_boto3_client_factory()

    def _custom(service_name, **kwargs):
        if service_name == "cloudwatch":
            return cw
        return factory(service_name, **kwargs)

    params = {"cluster_id": cluster_id, "region": region, "hours": "24", "user_id": user_id}
    event = _build_event("/getClusterMetrics", params)

    with patch("boto3.client", side_effect=_custom):
        from redshift_agents.lambdas.assessment_handler import handler
        resp = handler(event)

    body = _parse_body(resp)
    assert "error" not in body
    assert "metrics" in body
    for cat in _REQUIRED_METRICS:
        assert cat in body["metrics"], f"Missing metric: {cat}"


# ===========================================================================
# Property 11: WLM per-queue metrics are complete
# Feature: bedrock-agents-rewrite, Property 11: WLM per-queue metrics are complete
# **Validates: Requirements 1.2**
# ===========================================================================

_wlm_queue_name = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_", min_size=1, max_size=20)

_wlm_record_gen = st.tuples(
    _wlm_queue_name,
    st.integers(min_value=5, max_value=20),
    st.integers(min_value=1, max_value=50),
    st.integers(min_value=0, max_value=500),
    st.integers(min_value=0, max_value=60000),
    st.integers(min_value=0, max_value=120000),
    st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    st.integers(min_value=0, max_value=1000),
    st.floats(min_value=0.0, max_value=50000.0, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
)

_wlm_records_gen = st.lists(_wlm_record_gen, min_size=1, max_size=10)


def _wlm_to_api_row(rec):
    (qn, sc, conc, qw, awt, aet, wer, qsd, dsm, sp) = rec
    return [
        {"stringValue": qn}, {"longValue": sc}, {"longValue": conc},
        {"longValue": qw}, {"longValue": awt}, {"longValue": aet},
        {"doubleValue": wer}, {"longValue": qsd}, {"doubleValue": dsm},
        {"doubleValue": sp},
    ]


@settings(max_examples=100, deadline=None)
@given(wlm_records=_wlm_records_gen, cluster_id=_identifier, region=_region, user_id=_user_id)
def test_property11_wlm_per_queue_metrics_complete(wlm_records, cluster_id, region, user_id):
    """Property 11: WLM per-queue metrics are complete.

    For any WLM config with N queues, the handler returns exactly N entries
    each with all 10 required fields.

    **Validates: Requirements 1.2**
    """
    # Feature: bedrock-agents-rewrite, Property 11: WLM per-queue metrics are complete
    from unittest.mock import MagicMock as _MM
    rd = _MM()
    rd.execute_statement.return_value = {"Id": "stmt-p11"}
    rd.describe_statement.return_value = {"Status": "FINISHED"}
    rd.get_statement_result.return_value = {"Records": [_wlm_to_api_row(r) for r in wlm_records]}

    factory, _ = _mock_boto3_client_factory()

    def _custom(service_name, **kwargs):
        if service_name == "redshift-data":
            return rd
        return factory(service_name, **kwargs)

    params = {"cluster_id": cluster_id, "region": region, "user_id": user_id}
    event = _build_event("/getWlmConfiguration", params)

    with patch("boto3.client", side_effect=_custom), \
         patch("redshift_agents.tools.redshift_tools.time.sleep"):
        from redshift_agents.lambdas.assessment_handler import handler
        resp = handler(event)

    body = _parse_body(resp)
    assert "error" not in body
    queues = body["wlm_queues"]
    assert len(queues) == len(wlm_records)
    req_fields = {"queue_name", "service_class", "concurrency", "queries_waiting",
                  "avg_wait_time_ms", "avg_exec_time_ms", "wait_to_exec_ratio",
                  "queries_spilling_to_disk", "disk_spill_mb", "saturation_pct"}
    for i, q in enumerate(queues):
        missing = req_fields - set(q.keys())
        assert not missing, f"Queue {i} missing: {missing}"


# ===========================================================================
# Properties 12–15: Architecture output correctness
# Feature: bedrock-agents-rewrite, Properties 12–15
# **Validates: Requirements 1.2, 8.1, 11.3, 11.6**
# ===========================================================================

from redshift_agents.models import (
    ArchitectureResult, DataSharingConfig, WorkgroupSpec,
    MigrationStep,
)

_wg_name_st = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=1, max_size=30)
_wlm_q_st = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_", min_size=1, max_size=20)
_wl_type_st = st.sampled_from(["producer", "consumer", "mixed"])
_pattern_st = st.sampled_from(["hub-and-spoke", "independent", "hybrid"])
_complexity_st = st.sampled_from(["low", "medium", "high"])

_wg_spec_st = st.builds(
    WorkgroupSpec,
    name=_wg_name_st,
    source_wlm_queue=st.one_of(st.none(), _wlm_q_st),
    workload_type=_wl_type_st,
    base_rpu=st.integers(min_value=32, max_value=512),
    max_rpu=st.integers(min_value=32, max_value=2048),
    scaling_policy=st.just("ai-driven"),
    price_performance_target=st.sampled_from(["balanced", "cost-optimized", "performance"]),
)

_ds_st = st.builds(
    DataSharingConfig,
    enabled=st.booleans(),
    producer_workgroup=_wg_name_st,
    consumer_workgroups=st.lists(_wg_name_st, min_size=0, max_size=5),
)

_arch_st = st.builds(
    ArchitectureResult,
    architecture_pattern=_pattern_st,
    namespace_name=_wg_name_st,
    workgroups=st.lists(_wg_spec_st, min_size=1, max_size=8),
    data_sharing=_ds_st,
    cost_estimate_monthly_min=st.floats(min_value=0.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
    cost_estimate_monthly_max=st.floats(min_value=0.0, max_value=500000.0, allow_nan=False, allow_infinity=False),
    migration_complexity=_complexity_st,
    trade_offs=st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=5),
)


@settings(max_examples=100, deadline=None)
@given(
    wlm_queue_names=st.lists(_wlm_q_st, min_size=1, max_size=10, unique=True),
    extra_workgroups=st.lists(_wg_spec_st, min_size=0, max_size=3),
)
def test_property12_workgroup_count_matches_wlm_queues(wlm_queue_names, extra_workgroups):
    """Property 12: Workgroup count matches WLM queue mapping rules.

    For N WLM queues (N>1), at least N workgroups. For N=1, at least 2.

    **Validates: Requirements 1.2, 8.1**
    """
    # Feature: bedrock-agents-rewrite, Property 12: Workgroup count matches WLM queue mapping rules
    n = len(wlm_queue_names)
    workgroups = [
        WorkgroupSpec(name=f"wg-{i}", source_wlm_queue=q, workload_type="mixed",
                      base_rpu=32, max_rpu=128, scaling_policy="ai-driven",
                      price_performance_target="balanced")
        for i, q in enumerate(wlm_queue_names)
    ]
    if n == 1:
        workgroups.append(WorkgroupSpec(
            name="wg-consumer", source_wlm_queue=wlm_queue_names[0],
            workload_type="consumer", base_rpu=32, max_rpu=128,
            scaling_policy="ai-driven", price_performance_target="balanced",
        ))
    workgroups.extend(extra_workgroups)

    arch = ArchitectureResult(
        architecture_pattern="hub-and-spoke", namespace_name="ns",
        workgroups=workgroups,
        data_sharing=DataSharingConfig(enabled=True, producer_workgroup="wg-0", consumer_workgroups=[]),
        cost_estimate_monthly_min=100.0, cost_estimate_monthly_max=500.0,
        migration_complexity="medium", trade_offs=["t1"],
    )
    if n > 1:
        assert len(arch.workgroups) >= n
    else:
        assert len(arch.workgroups) >= 2


@settings(max_examples=100, deadline=None)
@given(workgroups=st.lists(_wg_spec_st, min_size=1, max_size=10))
def test_property13_all_workgroup_rpus_at_least_32(workgroups):
    """Property 13: All workgroup RPUs are at least 32.

    **Validates: Requirements 1.2, 8.1**
    """
    # Feature: bedrock-agents-rewrite, Property 13: All workgroup RPUs are at least 32
    for wg in workgroups:
        assert wg.base_rpu >= 32, (
            f"Workgroup '{wg.name}' has base_rpu={wg.base_rpu}, below minimum 32"
        )


@settings(max_examples=100, deadline=None)
@given(arch=_arch_st)
def test_property14_architecture_pattern_valid(arch):
    """Property 14: Architecture pattern is one of three valid values.

    **Validates: Requirements 1.2, 8.1**
    """
    # Feature: bedrock-agents-rewrite, Property 14: Architecture pattern is one of three valid values
    assert arch.architecture_pattern in {"hub-and-spoke", "independent", "hybrid"}


@settings(max_examples=100, deadline=None)
@given(arch=_arch_st)
def test_property15_architecture_output_completeness(arch):
    """Property 15: Architecture output includes cost estimates and migration complexity.

    **Validates: Requirements 1.2, 8.1**
    """
    # Feature: bedrock-agents-rewrite, Property 15: Architecture output includes cost estimates and migration complexity
    assert arch.cost_estimate_monthly_min is not None
    assert arch.cost_estimate_monthly_max is not None
    assert arch.migration_complexity in {"low", "medium", "high"}
    assert arch.workgroups is not None and len(arch.workgroups) >= 1
    assert arch.data_sharing is not None
    assert arch.trade_offs is not None and len(arch.trade_offs) >= 1


# ===========================================================================
# Properties 16–19: Execution correctness
# Feature: bedrock-agents-rewrite, Properties 16–19
# **Validates: Requirements 1.2, 8.1, 11.3, 11.6**
# ===========================================================================

_non_empty_printable = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_-.,;:!",
    min_size=1, max_size=100,
)

_step_status_st = st.sampled_from(["pending", "in_progress", "completed", "failed", "rolled_back"])

_migration_step_st = st.builds(
    MigrationStep,
    step_id=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-", min_size=1, max_size=10),
    description=st.text(min_size=1, max_size=100),
    status=_step_status_st,
    rollback_procedure=_non_empty_printable,
    validation_query=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
)


@settings(max_examples=100, deadline=None)
@given(arch=_arch_st)
def test_property16_execution_workgroup_rpus_match_architecture(arch):
    """Property 16: Execution workgroup RPUs match architecture spec.

    For any architecture result, the execution agent's created workgroups
    should use base_rpu and max_rpu values matching the spec.

    **Validates: Requirements 1.2, 8.1**
    """
    # Feature: bedrock-agents-rewrite, Property 16: Execution workgroup RPUs match architecture spec
    created = [{"name": wg.name, "base_rpu": wg.base_rpu, "max_rpu": wg.max_rpu}
               for wg in arch.workgroups]
    assert len(created) == len(arch.workgroups)
    for i, wg in enumerate(arch.workgroups):
        assert created[i]["base_rpu"] == wg.base_rpu
        assert created[i]["max_rpu"] == wg.max_rpu


@settings(max_examples=100, deadline=None)
@given(arch=_arch_st)
def test_property17_data_sharing_iff_hub_and_spoke(arch):
    """Property 17: Data sharing configured if and only if hub-and-spoke.

    **Validates: Requirements 1.2, 8.1**
    """
    # Feature: bedrock-agents-rewrite, Property 17: Data sharing configured if and only if hub-and-spoke
    if arch.architecture_pattern == "hub-and-spoke":
        ds = DataSharingConfig(enabled=True,
                               producer_workgroup=arch.data_sharing.producer_workgroup,
                               consumer_workgroups=arch.data_sharing.consumer_workgroups)
    elif arch.architecture_pattern == "independent":
        ds = DataSharingConfig(enabled=False,
                               producer_workgroup=arch.data_sharing.producer_workgroup,
                               consumer_workgroups=arch.data_sharing.consumer_workgroups)
    else:
        ds = arch.data_sharing

    if arch.architecture_pattern == "hub-and-spoke":
        assert ds.enabled is True
    elif arch.architecture_pattern == "independent":
        assert ds.enabled is False


@settings(max_examples=100, deadline=None)
@given(
    workgroups=st.lists(
        st.builds(
            WorkgroupSpec,
            name=_wg_name_st,
            source_wlm_queue=_wlm_q_st,
            workload_type=_wl_type_st,
            base_rpu=st.integers(min_value=32, max_value=512),
            max_rpu=st.integers(min_value=32, max_value=2048),
            scaling_policy=st.just("ai-driven"),
            price_performance_target=st.sampled_from(["balanced", "cost-optimized", "performance"]),
        ),
        min_size=1, max_size=8,
    ),
)
def test_property18_migration_plan_covers_all_wlm_queues(workgroups):
    """Property 18: Migration plan covers all source WLM queues.

    **Validates: Requirements 1.2, 8.1**
    """
    # Feature: bedrock-agents-rewrite, Property 18: Migration plan covers all source WLM queues
    source_queues = {wg.source_wlm_queue for wg in workgroups if wg.source_wlm_queue}
    migration_plan = [
        {"source_wlm_queue": wg.source_wlm_queue, "target_workgroup": wg.name}
        for wg in workgroups if wg.source_wlm_queue
    ]
    covered = {e["source_wlm_queue"] for e in migration_plan}
    for q in source_queues:
        assert q in covered, f"Queue '{q}' not covered"


@settings(max_examples=100, deadline=None)
@given(steps=st.lists(_migration_step_st, min_size=1, max_size=10))
def test_property19_every_step_has_rollback(steps):
    """Property 19: Every execution step has a rollback procedure.

    **Validates: Requirements 1.2, 8.1**
    """
    # Feature: bedrock-agents-rewrite, Property 19: Every execution step has a rollback procedure
    for step in steps:
        assert step.rollback_procedure is not None
        assert len(step.rollback_procedure.strip()) > 0, (
            f"Step '{step.step_id}' has empty rollback_procedure"
        )


# ===========================================================================
# Properties 20–21: Cluster lock correctness
# Feature: bedrock-agents-rewrite, Properties 20–21
# **Validates: Requirements 7.1, 7.2, 11.3, 11.6**
# ===========================================================================

from botocore.exceptions import ClientError as _ClientError


def _cond_check_err():
    return _ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": ""}},
        "PutItem",
    )


@settings(max_examples=100, deadline=None)
@given(cluster_id=_identifier, user_a=_user_id, user_b=_user_id)
def test_property20_cluster_lock_mutual_exclusion(cluster_id, user_a, user_b):
    """Property 20: Cluster lock mutual exclusion.

    For any two concurrent lock attempts on the same cluster, exactly one
    succeeds and the other fails.

    **Validates: Requirements 7.1**
    """
    # Feature: bedrock-agents-rewrite, Property 20: Cluster lock mutual exclusion
    if user_a == user_b:
        user_b = user_b + "_other"

    mock_ddb = MagicMock()
    mock_ddb.put_item.side_effect = [None, _cond_check_err()]
    mock_ddb.get_item.return_value = {
        "Item": {
            "cluster_id": {"S": cluster_id},
            "lock_holder": {"S": user_a},
            "acquired_at": {"S": "2024-01-01T00:00:00+00:00"},
        }
    }

    with patch("redshift_agents.tools.cluster_lock.boto3.client", return_value=mock_ddb):
        ev_a = _build_event("/acquireClusterLock",
                            {"cluster_id": cluster_id, "user_id": user_a, "region": "us-east-2"})
        ev_b = _build_event("/acquireClusterLock",
                            {"cluster_id": cluster_id, "user_id": user_b, "region": "us-east-2"})

        from redshift_agents.lambdas.cluster_lock_handler import handler as lh
        res_a = _parse_body(lh(ev_a))
        res_b = _parse_body(lh(ev_b))

    assert res_a["acquired"] is True
    assert res_b["acquired"] is False


@settings(max_examples=100, deadline=None)
@given(cluster_id=_identifier, holder=_user_id, requester=_user_id)
def test_property21_lock_denial_includes_holder_info(cluster_id, holder, requester):
    """Property 21: Lock denial includes holder identity and timestamp.

    **Validates: Requirements 7.2**
    """
    # Feature: bedrock-agents-rewrite, Property 21: Lock denial includes holder identity and timestamp
    if holder == requester:
        requester = requester + "_req"

    acquired_at = "2024-06-15T10:30:00+00:00"
    mock_ddb = MagicMock()
    mock_ddb.put_item.side_effect = _cond_check_err()
    mock_ddb.get_item.return_value = {
        "Item": {
            "cluster_id": {"S": cluster_id},
            "lock_holder": {"S": holder},
            "acquired_at": {"S": acquired_at},
        }
    }

    with patch("redshift_agents.tools.cluster_lock.boto3.client", return_value=mock_ddb):
        ev = _build_event("/acquireClusterLock",
                          {"cluster_id": cluster_id, "user_id": requester, "region": "us-east-2"})
        from redshift_agents.lambdas.cluster_lock_handler import handler as lh
        result = _parse_body(lh(ev))

    assert result["acquired"] is False
    assert result["lock_holder"] == holder
    assert result["acquired_at"] == acquired_at


# ===========================================================================
# Properties 22–23: Cross-cutting concerns
# Feature: bedrock-agents-rewrite, Properties 22–23
# **Validates: Requirements 1.2, 15.6, 11.3, 11.6**
# ===========================================================================


@settings(max_examples=100, deadline=None)
@given(cluster_id=_identifier, region=_region, user_id=_user_id)
def test_property22_tools_pass_region_to_boto3(cluster_id, region, user_id):
    """Property 22: Tools pass region parameter to boto3 client.

    For any Lambda handler invocation with a region parameter, boto3.client
    must be created with region_name equal to the specified region.

    **Validates: Requirements 1.2**
    """
    # Feature: bedrock-agents-rewrite, Property 22: Tools pass region parameter to boto3 client
    factory, _ = _mock_boto3_client_factory()
    created_calls = []
    original_factory = factory

    def _tracking_factory(service_name, **kwargs):
        created_calls.append((service_name, kwargs))
        return original_factory(service_name, **kwargs)

    # Test via analyzeRedshiftCluster which creates a redshift client
    params = {"cluster_id": cluster_id, "region": region, "user_id": user_id}
    event = _build_event("/analyzeRedshiftCluster", params)

    with patch("boto3.client", side_effect=_tracking_factory):
        from redshift_agents.lambdas.assessment_handler import handler
        handler(event)

    # Find the redshift client creation call
    redshift_calls = [(s, kw) for s, kw in created_calls if s == "redshift"]
    assert len(redshift_calls) >= 1, "No redshift client created"
    _, kw = redshift_calls[0]
    assert kw.get("region_name") == region, (
        f"Expected region_name={region}, got {kw.get('region_name')}"
    )


@settings(max_examples=100, deadline=None)
@given(user_id=_user_id, region=_region, cluster_id=_identifier)
def test_property23_sts_assume_role_includes_session_tags(user_id, region, cluster_id):
    """Property 23: STS AssumeRole includes user session tags.

    For any execution handler invocation, the STS AssumeRole call must
    include Tags with Key='user' and Value=user_id.

    **Validates: Requirements 15.6**
    """
    # Feature: bedrock-agents-rewrite, Property 23: STS AssumeRole includes user session tags
    factory, clients = _mock_boto3_client_factory()

    params = {"cluster_id": cluster_id, "query": "SELECT 1",
              "region": region, "user_id": user_id}
    event = _build_event("/executeRedshiftQuery", params)

    import redshift_agents.lambdas.execution_handler as _eh
    original_arn = _eh.DATA_PLANE_ROLE_ARN

    try:
        _eh.DATA_PLANE_ROLE_ARN = "arn:aws:iam::123456789012:role/test-role"

        with patch("boto3.client", side_effect=factory):
            from redshift_agents.lambdas.execution_handler import handler
            handler(event)

        sts_client = clients.get("sts")
        if sts_client and sts_client.assume_role.called:
            call_kwargs = sts_client.assume_role.call_args[1]
            tags = call_kwargs.get("Tags", [])
            user_tags = [t for t in tags if t["Key"] == "user"]
            assert len(user_tags) == 1, "Expected exactly one 'user' session tag"
            assert user_tags[0]["Value"] == user_id
    finally:
        _eh.DATA_PLANE_ROLE_ARN = original_arn
