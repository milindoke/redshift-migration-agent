"""
Unit tests for Redshift tools via Lambda action group handlers.

These tests invoke Lambda handler functions with Bedrock Agent action group
events instead of calling @tool functions directly. All AWS calls are mocked
via unittest.mock.patch on boto3.client — no AWS credentials needed.

Validates: Requirements 1.1, 1.2, 11.1, 11.2, 11.5
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from redshift_agents.tests.conftest import build_action_group_event, parse_response_body
from redshift_agents.lambdas.assessment_handler import handler as assessment_handler
from redshift_agents.lambdas.execution_handler import handler as execution_handler


class TestAnalyzeRedshiftCluster:
    """Test analyzeRedshiftCluster via assessment Lambda handler."""

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('boto3.client')
    def test_successful_analysis(self, mock_boto3, mock_audit):
        mock_client = Mock()
        mock_client.describe_clusters.return_value = {
            'Clusters': [{
                'ClusterIdentifier': 'test-cluster',
                'NodeType': 'ra3.4xlarge',
                'NumberOfNodes': 4,
                'ClusterStatus': 'available',
                'ClusterVersion': '1.0',
                'AvailabilityZone': 'us-east-2a',
                'Encrypted': True,
                'KmsKeyId': 'arn:aws:kms:us-east-2:XXXXXXXXXXXX:key/XXXXXXXX',
                'PubliclyAccessible': False,
                'VpcId': 'vpc-12345678',
                'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-12345678'}],
                'EnhancedVpcRouting': True,
                'Endpoint': {
                    'Address': 'test-cluster.abc123.us-east-2.redshift.amazonaws.com',
                    'Port': 5439
                },
                'ClusterParameterGroups': [{'ParameterGroupName': 'default.redshift-1.0'}],
                'AutomatedSnapshotRetentionPeriod': 7,
                'PreferredMaintenanceWindow': 'sun:05:00-sun:05:30',
                'ClusterCreateTime': datetime(2024, 1, 1, 12, 0, 0),
                'MasterUsername': 'admin',
                'DBName': 'dev',
            }]
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/analyzeRedshiftCluster",
            {"cluster_id": "test-cluster", "region": "us-east-2", "user_id": "jane.doe"},
        )
        resp = assessment_handler(event)

        assert resp["messageVersion"] == "1.0"
        assert resp["response"]["httpStatusCode"] == 200
        result = parse_response_body(resp)

        assert result['cluster_identifier'] == 'test-cluster'
        assert result['node_type'] == 'ra3.4xlarge'
        assert result['number_of_nodes'] == 4
        assert result['cluster_status'] == 'available'
        assert result['encrypted'] is True
        assert result['vpc_id'] == 'vpc-12345678'
        assert result['publicly_accessible'] is False
        assert result['enhanced_vpc_routing'] is True
        assert result['region'] == 'us-east-2'

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('boto3.client')
    def test_cluster_not_found(self, mock_boto3, mock_audit):
        mock_client = Mock()
        mock_client.describe_clusters.side_effect = Exception('ClusterNotFound')
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/analyzeRedshiftCluster",
            {"cluster_id": "nonexistent-cluster", "region": "us-east-2", "user_id": "jane.doe"},
        )
        resp = assessment_handler(event)
        result = parse_response_body(resp)

        assert 'error' in result
        assert result['cluster_id'] == 'nonexistent-cluster'
        assert result['region'] == 'us-east-2'


class TestGetClusterMetrics:
    """Test getClusterMetrics via assessment Lambda handler."""

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('boto3.client')
    def test_successful_metrics_retrieval(self, mock_boto3, mock_audit):
        mock_client = Mock()
        mock_client.get_metric_statistics.return_value = {
            'Datapoints': [
                {'Timestamp': datetime(2024, 1, 1, 12, 0, 0), 'Average': 45.5, 'Maximum': 67.8, 'Minimum': 23.4},
                {'Timestamp': datetime(2024, 1, 1, 13, 0, 0), 'Average': 52.3, 'Maximum': 71.2, 'Minimum': 31.5},
            ]
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/getClusterMetrics",
            {"cluster_id": "test-cluster", "region": "us-east-2", "hours": "24", "user_id": "jane.doe"},
        )
        resp = assessment_handler(event)
        result = parse_response_body(resp)

        assert result['cluster_id'] == 'test-cluster'
        assert result['region'] == 'us-east-2'
        assert result['time_range_hours'] == 24
        assert 'metrics' in result
        assert mock_client.get_metric_statistics.call_count == 7

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('boto3.client')
    def test_no_datapoints_available(self, mock_boto3, mock_audit):
        mock_client = Mock()
        mock_client.get_metric_statistics.return_value = {'Datapoints': []}
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/getClusterMetrics",
            {"cluster_id": "test-cluster", "region": "us-east-2", "hours": "1", "user_id": "jane.doe"},
        )
        resp = assessment_handler(event)
        result = parse_response_body(resp)

        assert result['cluster_id'] == 'test-cluster'
        assert 'metrics' in result
        for metric_name, metric_data in result['metrics'].items():
            assert metric_data['error'] == 'No data available'


class TestListRedshiftClusters:
    """Test listRedshiftClusters via assessment Lambda handler."""

    @patch('boto3.client')
    def test_list_multiple_clusters(self, mock_boto3):
        mock_client = Mock()
        mock_client.describe_clusters.return_value = {
            'Clusters': [
                {
                    'ClusterIdentifier': 'cluster-1', 'NodeType': 'ra3.4xlarge',
                    'NumberOfNodes': 4, 'ClusterStatus': 'available',
                    'ClusterCreateTime': datetime(2024, 1, 1, 12, 0, 0),
                    'AvailabilityZone': 'us-east-2a', 'Encrypted': True,
                    'PubliclyAccessible': False,
                },
                {
                    'ClusterIdentifier': 'cluster-2', 'NodeType': 'dc2.large',
                    'NumberOfNodes': 2, 'ClusterStatus': 'available',
                    'ClusterCreateTime': datetime(2024, 1, 2, 12, 0, 0),
                    'AvailabilityZone': 'us-east-2b', 'Encrypted': False,
                    'PubliclyAccessible': True,
                }
            ]
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/listRedshiftClusters",
            {"region": "us-east-2", "user_id": "jane.doe"},
        )
        resp = assessment_handler(event)
        result = parse_response_body(resp)

        assert len(result) == 2
        assert result[0]['cluster_identifier'] == 'cluster-1'
        assert result[1]['cluster_identifier'] == 'cluster-2'

    @patch('boto3.client')
    def test_list_no_clusters(self, mock_boto3):
        mock_client = Mock()
        mock_client.describe_clusters.return_value = {'Clusters': []}
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/listRedshiftClusters",
            {"region": "us-east-2", "user_id": "jane.doe"},
        )
        resp = assessment_handler(event)
        result = parse_response_body(resp)
        assert result == []

    @patch('boto3.client')
    def test_list_clusters_error(self, mock_boto3):
        mock_client = Mock()
        mock_client.describe_clusters.side_effect = Exception('AccessDenied')
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/listRedshiftClusters",
            {"region": "us-east-2", "user_id": "jane.doe"},
        )
        resp = assessment_handler(event)
        result = parse_response_body(resp)
        assert 'error' in result


class TestGetWlmConfiguration:
    """Test getWlmConfiguration via assessment Lambda handler."""

    @patch('redshift_agents.tools.redshift_tools.time.sleep')
    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('boto3.client')
    def test_successful_wlm_query(self, mock_boto3, mock_audit, mock_sleep):
        mock_client = Mock()
        mock_client.execute_statement.return_value = {'Id': 'stmt-123'}
        mock_client.describe_statement.return_value = {'Status': 'FINISHED'}
        mock_client.get_statement_result.return_value = {
            'Records': [
                [
                    {'stringValue': 'etl_queue'}, {'longValue': 6}, {'longValue': 5},
                    {'longValue': 0}, {'longValue': 0}, {'longValue': 0},
                    {'doubleValue': 0.0}, {'longValue': 0}, {'doubleValue': 0.0}, {'doubleValue': 0.0},
                ],
                [
                    {'stringValue': 'analytics_queue'}, {'longValue': 7}, {'longValue': 10},
                    {'longValue': 0}, {'longValue': 0}, {'longValue': 0},
                    {'doubleValue': 0.0}, {'longValue': 0}, {'doubleValue': 0.0}, {'doubleValue': 0.0},
                ],
            ]
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/getWlmConfiguration",
            {"cluster_id": "test-cluster", "region": "us-east-2", "user_id": "jane.doe"},
        )
        resp = assessment_handler(event)
        result = parse_response_body(resp)

        assert 'error' not in result
        assert result['cluster_id'] == 'test-cluster'
        assert len(result['wlm_queues']) == 2
        assert result['wlm_queues'][0]['queue_name'] == 'etl_queue'

        call_kwargs = mock_client.execute_statement.call_args[1]
        assert call_kwargs['DbUser'] == 'jane.doe'

    @patch('redshift_agents.tools.redshift_tools.time.sleep')
    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('boto3.client')
    def test_query_failed(self, mock_boto3, mock_audit, mock_sleep):
        mock_client = Mock()
        mock_client.execute_statement.return_value = {'Id': 'stmt-456'}
        mock_client.describe_statement.return_value = {'Status': 'FAILED', 'Error': 'Permission denied'}
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/getWlmConfiguration",
            {"cluster_id": "test-cluster", "region": "us-east-2", "user_id": "jane.doe"},
        )
        resp = assessment_handler(event)
        result = parse_response_body(resp)
        assert 'error' in result

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('boto3.client')
    def test_exception_handling(self, mock_boto3, mock_audit):
        mock_client = Mock()
        mock_client.execute_statement.side_effect = Exception('Connection refused')
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/getWlmConfiguration",
            {"cluster_id": "test-cluster", "region": "us-east-2", "user_id": "jane.doe"},
        )
        resp = assessment_handler(event)
        result = parse_response_body(resp)
        assert 'error' in result

    @patch('redshift_agents.tools.redshift_tools.time.sleep')
    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('boto3.client')
    def test_empty_results(self, mock_boto3, mock_audit, mock_sleep):
        mock_client = Mock()
        mock_client.execute_statement.return_value = {'Id': 'stmt-789'}
        mock_client.describe_statement.return_value = {'Status': 'FINISHED'}
        mock_client.get_statement_result.return_value = {'Records': []}
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/getWlmConfiguration",
            {"cluster_id": "test-cluster", "region": "us-east-2", "user_id": "jane.doe"},
        )
        resp = assessment_handler(event)
        result = parse_response_body(resp)
        assert result['wlm_queues'] == []


class TestExecuteRedshiftQuery:
    """Test executeRedshiftQuery via execution Lambda handler."""

    @patch('redshift_agents.tools.redshift_tools.time.sleep')
    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('boto3.client')
    def test_successful_query_execution(self, mock_boto3, mock_audit, mock_sleep):
        mock_client = Mock()
        mock_client.execute_statement.return_value = {'Id': 'stmt-exec-1'}
        mock_client.describe_statement.return_value = {'Status': 'FINISHED'}
        mock_client.get_statement_result.return_value = {
            'Records': [
                [{'stringValue': 'row1_col1'}, {'longValue': 42}],
                [{'stringValue': 'row2_col1'}, {'longValue': 99}],
            ]
        }
        mock_client.assume_role.return_value = {
            'Credentials': {'AccessKeyId': 'x', 'SecretAccessKey': 'y', 'SessionToken': 'z', 'Expiration': '2099-01-01'}
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/executeRedshiftQuery",
            {"cluster_id": "test-cluster", "query": "SELECT * FROM my_table",
             "region": "us-east-2", "user_id": "jane.doe"},
        )
        resp = execution_handler(event)
        result = parse_response_body(resp)

        assert 'error' not in result
        assert result['cluster_id'] == 'test-cluster'
        assert len(result['records']) == 2

    @patch('redshift_agents.tools.redshift_tools.time.sleep')
    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('boto3.client')
    def test_query_failure(self, mock_boto3, mock_audit, mock_sleep):
        mock_client = Mock()
        mock_client.execute_statement.return_value = {'Id': 'stmt-exec-2'}
        mock_client.describe_statement.return_value = {'Status': 'FAILED', 'Error': 'Syntax error in SQL'}
        mock_client.assume_role.return_value = {
            'Credentials': {'AccessKeyId': 'x', 'SecretAccessKey': 'y', 'SessionToken': 'z', 'Expiration': '2099-01-01'}
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/executeRedshiftQuery",
            {"cluster_id": "test-cluster", "query": "INVALID SQL",
             "region": "us-east-2", "user_id": "jane.doe"},
        )
        resp = execution_handler(event)
        result = parse_response_body(resp)
        assert 'error' in result

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('boto3.client')
    def test_exception_handling(self, mock_boto3, mock_audit):
        mock_client = Mock()
        mock_client.execute_statement.side_effect = Exception('Connection refused')
        mock_client.assume_role.return_value = {
            'Credentials': {'AccessKeyId': 'x', 'SecretAccessKey': 'y', 'SessionToken': 'z', 'Expiration': '2099-01-01'}
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/executeRedshiftQuery",
            {"cluster_id": "test-cluster", "query": "SELECT 1",
             "region": "us-east-2", "user_id": "jane.doe"},
        )
        resp = execution_handler(event)
        result = parse_response_body(resp)
        assert 'error' in result


class TestCreateServerlessNamespace:
    """Test createServerlessNamespace via execution Lambda handler."""

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('boto3.client')
    def test_successful_namespace_creation(self, mock_boto3, mock_audit):
        mock_client = Mock()
        mock_client.create_namespace.return_value = {
            'namespace': {
                'namespaceName': 'my-namespace', 'namespaceId': 'ns-abc123',
                'namespaceArn': 'arn:aws:redshift-serverless:us-east-2:XXXXXXXXXXXX:namespace/ns-abc123',
                'status': 'AVAILABLE', 'adminUsername': 'admin', 'dbName': 'dev',
            }
        }
        mock_client.assume_role.return_value = {
            'Credentials': {'AccessKeyId': 'x', 'SecretAccessKey': 'y', 'SessionToken': 'z', 'Expiration': '2099-01-01'}
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/createServerlessNamespace",
            {"namespace_name": "my-namespace", "admin_username": "admin",
             "db_name": "dev", "region": "us-east-2", "user_id": "jane.doe"},
        )
        resp = execution_handler(event)
        result = parse_response_body(resp)

        assert result['namespace_name'] == 'my-namespace'
        assert result['status'] == 'AVAILABLE'
        assert 'error' not in result

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('boto3.client')
    def test_namespace_creation_error(self, mock_boto3, mock_audit):
        mock_client = Mock()
        mock_client.create_namespace.side_effect = Exception('ConflictException: Namespace already exists')
        mock_client.assume_role.return_value = {
            'Credentials': {'AccessKeyId': 'x', 'SecretAccessKey': 'y', 'SessionToken': 'z', 'Expiration': '2099-01-01'}
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/createServerlessNamespace",
            {"namespace_name": "my-namespace", "region": "us-east-2", "user_id": "jane.doe"},
        )
        resp = execution_handler(event)
        result = parse_response_body(resp)
        assert 'error' in result


class TestCreateServerlessWorkgroup:
    """Test createServerlessWorkgroup via execution Lambda handler."""

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('boto3.client')
    def test_successful_workgroup_creation(self, mock_boto3, mock_audit):
        mock_client = Mock()
        mock_client.create_workgroup.return_value = {
            'workgroup': {
                'workgroupName': 'my-workgroup', 'workgroupId': 'wg-abc123',
                'workgroupArn': 'arn:aws:redshift-serverless:us-east-2:XXXXXXXXXXXX:workgroup/wg-abc123',
                'status': 'AVAILABLE', 'namespaceName': 'my-namespace',
                'baseCapacity': 32, 'maxCapacity': 512,
            }
        }
        mock_client.assume_role.return_value = {
            'Credentials': {'AccessKeyId': 'x', 'SecretAccessKey': 'y', 'SessionToken': 'z', 'Expiration': '2099-01-01'}
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/createServerlessWorkgroup",
            {"workgroup_name": "my-workgroup", "namespace_name": "my-namespace",
             "base_rpu": "32", "max_rpu": "512", "region": "us-east-2", "user_id": "jane.doe"},
        )
        resp = execution_handler(event)
        result = parse_response_body(resp)

        assert result['workgroup_name'] == 'my-workgroup'
        assert result['status'] == 'AVAILABLE'
        assert 'error' not in result

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('boto3.client')
    def test_workgroup_creation_error(self, mock_boto3, mock_audit):
        mock_client = Mock()
        mock_client.create_workgroup.side_effect = Exception('ConflictException')
        mock_client.assume_role.return_value = {
            'Credentials': {'AccessKeyId': 'x', 'SecretAccessKey': 'y', 'SessionToken': 'z', 'Expiration': '2099-01-01'}
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/createServerlessWorkgroup",
            {"workgroup_name": "my-workgroup", "namespace_name": "my-namespace",
             "region": "us-east-2", "user_id": "jane.doe"},
        )
        resp = execution_handler(event)
        result = parse_response_body(resp)
        assert 'error' in result


class TestRestoreSnapshotToServerless:
    """Test restoreSnapshotToServerless via execution Lambda handler."""

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('boto3.client')
    def test_successful_restore(self, mock_boto3, mock_audit):
        mock_client = Mock()
        mock_client.restore_from_snapshot.return_value = {
            'namespace': {
                'namespaceName': 'my-namespace', 'namespaceId': 'ns-restore123',
                'namespaceArn': 'arn:aws:redshift-serverless:us-east-2:XXXXXXXXXXXX:namespace/ns-restore123',
                'status': 'RESTORING',
            }
        }
        mock_client.assume_role.return_value = {
            'Credentials': {'AccessKeyId': 'x', 'SecretAccessKey': 'y', 'SessionToken': 'z', 'Expiration': '2099-01-01'}
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/restoreSnapshotToServerless",
            {"snapshot_identifier": "my-snapshot", "namespace_name": "my-namespace",
             "region": "us-east-2", "user_id": "jane.doe"},
        )
        resp = execution_handler(event)
        result = parse_response_body(resp)

        assert result['namespace_name'] == 'my-namespace'
        assert result['status'] == 'RESTORING'
        assert 'error' not in result

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('boto3.client')
    def test_restore_error(self, mock_boto3, mock_audit):
        mock_client = Mock()
        mock_client.restore_from_snapshot.side_effect = Exception('SnapshotNotFound')
        mock_client.assume_role.return_value = {
            'Credentials': {'AccessKeyId': 'x', 'SecretAccessKey': 'y', 'SessionToken': 'z', 'Expiration': '2099-01-01'}
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/restoreSnapshotToServerless",
            {"snapshot_identifier": "bad-snapshot", "namespace_name": "my-namespace",
             "region": "us-east-2", "user_id": "jane.doe"},
        )
        resp = execution_handler(event)
        result = parse_response_body(resp)
        assert 'error' in result


class TestSetupDataSharing:
    """Test setupDataSharing via execution Lambda handler."""

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('boto3.client')
    def test_successful_data_sharing_setup(self, mock_boto3, mock_audit):
        mock_serverless = Mock()
        mock_data = Mock()

        mock_serverless.get_namespace.side_effect = [
            {'namespace': {'namespaceName': 'producer-ns', 'namespaceId': 'ns-prod-001'}},
            {'namespace': {'namespaceName': 'consumer-ns-1', 'namespaceId': 'ns-con-001'}},
            {'namespace': {'namespaceName': 'consumer-ns-2', 'namespaceId': 'ns-con-002'}},
        ]
        mock_data.execute_statement.return_value = {'Id': 'stmt-ds-1'}
        mock_serverless.assume_role.return_value = {
            'Credentials': {'AccessKeyId': 'x', 'SecretAccessKey': 'y', 'SessionToken': 'z', 'Expiration': '2099-01-01'}
        }

        def route_client(service, **kwargs):
            if service == 'redshift-serverless':
                return mock_serverless
            if service == 'sts':
                return mock_serverless
            return mock_data

        mock_boto3.side_effect = route_client

        event = build_action_group_event(
            "/setupDataSharing",
            {"producer_namespace": "producer-ns", "consumer_namespaces": "consumer-ns-1, consumer-ns-2",
             "datashare_name": "my_share", "region": "us-east-2", "user_id": "jane.doe"},
        )
        resp = execution_handler(event)
        result = parse_response_body(resp)

        assert 'error' not in result
        assert result['datashare_name'] == 'my_share'
        assert result['producer_namespace'] == 'producer-ns'
        assert len(result['consumer_namespaces']) == 2

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('boto3.client')
    def test_data_sharing_error_handling(self, mock_boto3, mock_audit):
        mock_client = Mock()
        mock_client.get_namespace.side_effect = Exception('NamespaceNotFound')
        mock_client.assume_role.return_value = {
            'Credentials': {'AccessKeyId': 'x', 'SecretAccessKey': 'y', 'SessionToken': 'z', 'Expiration': '2099-01-01'}
        }
        mock_boto3.return_value = mock_client

        event = build_action_group_event(
            "/setupDataSharing",
            {"producer_namespace": "producer-ns", "consumer_namespaces": "consumer-ns-1",
             "region": "us-east-2", "user_id": "jane.doe"},
        )
        resp = execution_handler(event)
        result = parse_response_body(resp)
        assert 'error' in result
