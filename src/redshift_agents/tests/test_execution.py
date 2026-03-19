"""
Tests for execution Lambda handler dispatch for all 5 operations.

Includes STS AssumeRole with session tags verification.

Validates: Requirements 11.1, 11.5, 11.6, 15.6
"""
from __future__ import annotations

from unittest.mock import Mock, MagicMock, patch

from redshift_agents.lambdas.execution_handler import handler as execution_handler
from redshift_agents.tests.conftest import build_action_group_event, parse_response_body


def _mock_sts_client():
    """Return a mock that handles STS assume_role."""
    m = MagicMock()
    m.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "AKIA...", "SecretAccessKey": "secret",
            "SessionToken": "token", "Expiration": "2099-01-01T00:00:00Z",
        }
    }
    return m


class TestExecutionHandlerDispatch:
    """Verify execution handler dispatches all 5 apiPaths correctly."""

    @patch("redshift_agents.tools.redshift_tools.time.sleep")
    @patch("redshift_agents.tools.redshift_tools.emit_audit_event")
    @patch("boto3.client")
    def test_execute_redshift_query(self, mock_boto3, mock_audit, mock_sleep):
        mock_client = Mock()
        mock_client.execute_statement.return_value = {"Id": "stmt-1"}
        mock_client.describe_statement.return_value = {"Status": "FINISHED"}
        mock_client.get_statement_result.return_value = {"Records": []}
        mock_client.assume_role.return_value = {
            "Credentials": {"AccessKeyId": "x", "SecretAccessKey": "y",
                            "SessionToken": "z", "Expiration": "2099-01-01"}
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/executeRedshiftQuery",
            {"cluster_id": "c1", "query": "SELECT 1", "region": "us-east-2", "user_id": "alice"},
        )
        resp = execution_handler(event)
        assert resp["response"]["apiPath"] == "/executeRedshiftQuery"
        result = parse_response_body(resp)
        assert "records" in result

        # Verify DbUser identity propagation
        call_kwargs = mock_client.execute_statement.call_args[1]
        assert call_kwargs["DbUser"] == "alice"

    @patch("redshift_agents.tools.redshift_tools.emit_audit_event")
    @patch("boto3.client")
    def test_create_serverless_namespace(self, mock_boto3, mock_audit):
        mock_client = Mock()
        mock_client.create_namespace.return_value = {
            "namespace": {
                "namespaceName": "ns1", "namespaceId": "id-1",
                "namespaceArn": "arn:...", "status": "AVAILABLE",
                "adminUsername": "admin", "dbName": "dev",
            }
        }
        mock_client.assume_role.return_value = {
            "Credentials": {"AccessKeyId": "x", "SecretAccessKey": "y",
                            "SessionToken": "z", "Expiration": "2099-01-01"}
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/createServerlessNamespace",
            {"namespace_name": "ns1", "region": "us-east-2", "user_id": "alice"},
        )
        resp = execution_handler(event)
        result = parse_response_body(resp)
        assert result["namespace_name"] == "ns1"

    @patch("redshift_agents.tools.redshift_tools.emit_audit_event")
    @patch("boto3.client")
    def test_create_serverless_workgroup(self, mock_boto3, mock_audit):
        mock_client = Mock()
        mock_client.create_workgroup.return_value = {
            "workgroup": {
                "workgroupName": "wg1", "workgroupId": "wg-id-1",
                "workgroupArn": "arn:...", "status": "AVAILABLE",
                "namespaceName": "ns1", "baseCapacity": 32, "maxCapacity": 512,
            }
        }
        mock_client.assume_role.return_value = {
            "Credentials": {"AccessKeyId": "x", "SecretAccessKey": "y",
                            "SessionToken": "z", "Expiration": "2099-01-01"}
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/createServerlessWorkgroup",
            {"workgroup_name": "wg1", "namespace_name": "ns1",
             "base_rpu": "32", "max_rpu": "512", "region": "us-east-2", "user_id": "alice"},
        )
        resp = execution_handler(event)
        result = parse_response_body(resp)
        assert result["workgroup_name"] == "wg1"

    @patch("redshift_agents.tools.redshift_tools.emit_audit_event")
    @patch("boto3.client")
    def test_restore_snapshot_to_serverless(self, mock_boto3, mock_audit):
        mock_client = Mock()
        mock_client.restore_from_snapshot.return_value = {
            "namespace": {
                "namespaceName": "ns1", "namespaceId": "id-1",
                "namespaceArn": "arn:...", "status": "RESTORING",
            }
        }
        mock_client.assume_role.return_value = {
            "Credentials": {"AccessKeyId": "x", "SecretAccessKey": "y",
                            "SessionToken": "z", "Expiration": "2099-01-01"}
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/restoreSnapshotToServerless",
            {"snapshot_identifier": "snap1", "namespace_name": "ns1",
             "region": "us-east-2", "user_id": "alice"},
        )
        resp = execution_handler(event)
        result = parse_response_body(resp)
        assert result["status"] == "RESTORING"

    @patch("redshift_agents.tools.redshift_tools.emit_audit_event")
    @patch("boto3.client")
    def test_setup_data_sharing(self, mock_boto3, mock_audit):
        mock_serverless = Mock()
        mock_data = Mock()
        mock_serverless.get_namespace.side_effect = [
            {"namespace": {"namespaceName": "prod", "namespaceId": "ns-prod"}},
            {"namespace": {"namespaceName": "cons", "namespaceId": "ns-cons"}},
        ]
        mock_data.execute_statement.return_value = {"Id": "stmt-1"}
        mock_serverless.assume_role.return_value = {
            "Credentials": {"AccessKeyId": "x", "SecretAccessKey": "y",
                            "SessionToken": "z", "Expiration": "2099-01-01"}
        }

        def route(service, **kwargs):
            if service == "redshift-serverless":
                return mock_serverless
            if service == "sts":
                return mock_serverless
            return mock_data

        mock_boto3.side_effect = route

        event = build_action_group_event(
            "/setupDataSharing",
            {"producer_namespace": "prod", "consumer_namespaces": "cons",
             "region": "us-east-2", "user_id": "alice"},
        )
        resp = execution_handler(event)
        result = parse_response_body(resp)
        assert result["datashare_name"] == "default_share"

    @patch("boto3.client")
    def test_unknown_api_path(self, mock_boto3):
        mock_client = Mock()
        mock_client.assume_role.return_value = {
            "Credentials": {"AccessKeyId": "x", "SecretAccessKey": "y",
                            "SessionToken": "z", "Expiration": "2099-01-01"}
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/unknownOperation",
            {"user_id": "alice"},
        )
        resp = execution_handler(event)
        result = parse_response_body(resp)
        assert "error" in result

    @patch("redshift_agents.lambdas.execution_handler.DATA_PLANE_ROLE_ARN", "arn:aws:iam::123:role/test")
    @patch("redshift_agents.tools.redshift_tools.time.sleep")
    @patch("redshift_agents.tools.redshift_tools.emit_audit_event")
    @patch("boto3.client")
    def test_sts_assume_role_with_session_tags(self, mock_boto3, mock_audit, mock_sleep):
        """Verify STS AssumeRole includes user session tags (Requirement 15.6)."""
        import redshift_agents.lambdas.execution_handler as _eh
        mock_client = Mock()
        mock_client.execute_statement.return_value = {"Id": "stmt-1"}
        mock_client.describe_statement.return_value = {"Status": "FINISHED"}
        mock_client.get_statement_result.return_value = {"Records": []}
        mock_client.assume_role.return_value = {
            "Credentials": {"AccessKeyId": "x", "SecretAccessKey": "y",
                            "SessionToken": "z", "Expiration": "2099-01-01"}
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/executeRedshiftQuery",
            {"cluster_id": "c1", "query": "SELECT 1", "region": "us-east-2", "user_id": "alice"},
        )
        _eh.handler(event)

        # Verify STS AssumeRole was called with session tags
        mock_client.assume_role.assert_called_once()
        call_kwargs = mock_client.assume_role.call_args[1]
        assert call_kwargs["Tags"] == [{"Key": "user", "Value": "alice"}]
        assert "alice" in call_kwargs["RoleSessionName"]
