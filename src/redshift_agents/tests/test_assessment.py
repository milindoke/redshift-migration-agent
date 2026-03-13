"""
Tests for assessment Lambda handler dispatch for all 4 operations.

Validates: Requirements 11.1, 11.5
"""
from __future__ import annotations

from unittest.mock import Mock, patch

from redshift_agents.lambdas.assessment_handler import handler as assessment_handler
from redshift_agents.tests.conftest import build_action_group_event, parse_response_body


class TestAssessmentHandlerDispatch:
    """Verify assessment handler dispatches all 4 apiPaths correctly."""

    @patch("redshift_agents.tools.redshift_tools.emit_audit_event")
    @patch("boto3.client")
    def test_list_redshift_clusters(self, mock_boto3, mock_audit):
        mock_client = Mock()
        mock_client.describe_clusters.return_value = {
            "Clusters": [
                {
                    "ClusterIdentifier": "c1", "NodeType": "ra3.xlplus",
                    "NumberOfNodes": 2, "ClusterStatus": "available",
                    "ClusterCreateTime": "2024-01-01", "AvailabilityZone": "us-east-1a",
                    "Encrypted": True, "PubliclyAccessible": False,
                }
            ]
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/listRedshiftClusters",
            {"region": "us-east-1", "user_id": "alice"},
        )
        resp = assessment_handler(event)

        assert resp["messageVersion"] == "1.0"
        assert resp["response"]["apiPath"] == "/listRedshiftClusters"
        result = parse_response_body(resp)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["cluster_identifier"] == "c1"

    @patch("redshift_agents.tools.redshift_tools.emit_audit_event")
    @patch("boto3.client")
    def test_analyze_redshift_cluster(self, mock_boto3, mock_audit):
        mock_client = Mock()
        mock_client.describe_clusters.return_value = {
            "Clusters": [{
                "ClusterIdentifier": "c1", "NodeType": "ra3.4xlarge",
                "NumberOfNodes": 4, "ClusterStatus": "available",
                "ClusterVersion": "1.0", "AvailabilityZone": "us-east-2a",
                "Encrypted": True, "KmsKeyId": "key-1",
                "PubliclyAccessible": False, "VpcId": "vpc-123",
                "VpcSecurityGroups": [], "EnhancedVpcRouting": True,
                "Endpoint": {"Address": "host", "Port": 5439},
                "ClusterParameterGroups": [{"ParameterGroupName": "default"}],
                "AutomatedSnapshotRetentionPeriod": 7,
                "PreferredMaintenanceWindow": "sun:05:00-sun:06:00",
                "ClusterCreateTime": "2024-01-01", "MasterUsername": "admin",
                "DBName": "dev",
            }]
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/analyzeRedshiftCluster",
            {"cluster_id": "c1", "region": "us-east-2", "user_id": "alice"},
        )
        resp = assessment_handler(event)
        result = parse_response_body(resp)
        assert result["cluster_identifier"] == "c1"
        assert result["node_type"] == "ra3.4xlarge"

    @patch("redshift_agents.tools.redshift_tools.emit_audit_event")
    @patch("boto3.client")
    def test_get_cluster_metrics(self, mock_boto3, mock_audit):
        mock_client = Mock()
        mock_client.get_metric_statistics.return_value = {
            "Datapoints": [{"Average": 50.0, "Maximum": 80.0, "Minimum": 20.0}]
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/getClusterMetrics",
            {"cluster_id": "c1", "region": "us-east-2", "hours": "24", "user_id": "alice"},
        )
        resp = assessment_handler(event)
        result = parse_response_body(resp)
        assert "metrics" in result
        assert result["cluster_id"] == "c1"

    @patch("redshift_agents.tools.redshift_tools.time.sleep")
    @patch("redshift_agents.tools.redshift_tools.emit_audit_event")
    @patch("boto3.client")
    def test_get_wlm_configuration(self, mock_boto3, mock_audit, mock_sleep):
        mock_client = Mock()
        mock_client.execute_statement.return_value = {"Id": "stmt-1"}
        mock_client.describe_statement.return_value = {"Status": "FINISHED"}
        mock_client.get_statement_result.return_value = {"Records": []}
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/getWlmConfiguration",
            {"cluster_id": "c1", "region": "us-east-2", "user_id": "alice"},
        )
        resp = assessment_handler(event)
        result = parse_response_body(resp)
        assert "wlm_queues" in result

    @patch("boto3.client")
    def test_unknown_api_path(self, mock_boto3):
        event = build_action_group_event(
            "/unknownOperation",
            {"user_id": "alice"},
        )
        resp = assessment_handler(event)
        result = parse_response_body(resp)
        assert "error" in result
        assert "Unknown" in result["error"]
