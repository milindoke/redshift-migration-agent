"""
Unit tests for Redshift tools.

These tests run locally without AWS credentials by mocking boto3 responses.
This is TRUE local testing - no AWS access needed!
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the tools we want to test
from redshift_agents.tools.redshift_tools import (
    analyze_redshift_cluster,
    create_serverless_namespace,
    create_serverless_workgroup,
    execute_redshift_query,
    get_cluster_metrics,
    get_wlm_configuration,
    list_redshift_clusters,
    restore_snapshot_to_serverless,
    setup_data_sharing,
)


class TestAnalyzeRedshiftCluster:
    """Test the analyze_redshift_cluster function."""
    
    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_successful_analysis(self, mock_boto3, mock_audit):
        """Test successful cluster analysis."""
        # Mock AWS Redshift response
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
        
        # Call the function with user_id
        result = analyze_redshift_cluster('test-cluster', 'us-east-2', user_id='jane.doe')
        
        # Assertions
        assert result['cluster_identifier'] == 'test-cluster'
        assert result['node_type'] == 'ra3.4xlarge'
        assert result['number_of_nodes'] == 4
        assert result['cluster_status'] == 'available'
        assert result['cluster_version'] == '1.0'
        assert result['encrypted'] == True
        assert result['vpc_id'] == 'vpc-12345678'
        assert result['publicly_accessible'] == False
        assert result['enhanced_vpc_routing'] == True
        assert result['region'] == 'us-east-2'
        
        # Verify boto3 was called correctly
        mock_boto3.assert_called_once_with('redshift', region_name='us-east-2')
        mock_client.describe_clusters.assert_called_once_with(ClusterIdentifier='test-cluster')
        
        # Verify audit event was emitted with user_id
        mock_audit.assert_called_once_with(
            "tool_invocation",
            "assessment",
            initiated_by='jane.doe',
            cluster_id='test-cluster',
            region='us-east-2',
            details={"tool": "analyze_redshift_cluster"},
        )
    
    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_cluster_not_found(self, mock_boto3, mock_audit):
        """Test handling of cluster not found error."""
        # Mock AWS error
        mock_client = Mock()
        mock_client.describe_clusters.side_effect = Exception('ClusterNotFound')
        mock_boto3.return_value = mock_client
        
        # Call the function with user_id
        result = analyze_redshift_cluster('nonexistent-cluster', 'us-east-2', user_id='jane.doe')
        
        # Assertions
        assert 'error' in result
        assert result['cluster_id'] == 'nonexistent-cluster'
        assert result['region'] == 'us-east-2'


class TestGetClusterMetrics:
    """Test the get_cluster_metrics function."""
    
    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_successful_metrics_retrieval(self, mock_boto3, mock_audit):
        """Test successful metrics retrieval."""
        # Mock CloudWatch response
        mock_client = Mock()
        mock_client.get_metric_statistics.return_value = {
            'Datapoints': [
                {
                    'Timestamp': datetime(2024, 1, 1, 12, 0, 0),
                    'Average': 45.5,
                    'Maximum': 67.8,
                    'Minimum': 23.4,
                },
                {
                    'Timestamp': datetime(2024, 1, 1, 13, 0, 0),
                    'Average': 52.3,
                    'Maximum': 71.2,
                    'Minimum': 31.5,
                }
            ]
        }
        mock_boto3.return_value = mock_client
        
        # Call the function with user_id
        result = get_cluster_metrics('test-cluster', 'us-east-2', hours=24, user_id='jane.doe')
        
        # Assertions
        assert result['cluster_id'] == 'test-cluster'
        assert result['region'] == 'us-east-2'
        assert result['time_range_hours'] == 24
        assert 'metrics' in result
        assert 'timestamp' in result
        
        # Verify CloudWatch was called for each metric
        assert mock_client.get_metric_statistics.call_count == 7  # 7 metrics
        
        # Verify audit event was emitted with user_id
        mock_audit.assert_called_once_with(
            "tool_invocation",
            "assessment",
            initiated_by='jane.doe',
            cluster_id='test-cluster',
            region='us-east-2',
            details={"tool": "get_cluster_metrics", "hours": 24},
        )
    
    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_no_datapoints_available(self, mock_boto3, mock_audit):
        """Test handling when no metrics are available."""
        # Mock CloudWatch response with no datapoints
        mock_client = Mock()
        mock_client.get_metric_statistics.return_value = {'Datapoints': []}
        mock_boto3.return_value = mock_client
        
        # Call the function with user_id
        result = get_cluster_metrics('test-cluster', 'us-east-2', hours=1, user_id='jane.doe')
        
        # Assertions
        assert result['cluster_id'] == 'test-cluster'
        assert 'metrics' in result
        # All metrics should have 'error': 'No data available'
        for metric_name, metric_data in result['metrics'].items():
            assert metric_data['error'] == 'No data available'


class TestListRedshiftClusters:
    """Test the list_redshift_clusters function."""
    
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_list_multiple_clusters(self, mock_boto3):
        """Test listing multiple clusters."""
        # Mock AWS response
        mock_client = Mock()
        mock_client.describe_clusters.return_value = {
            'Clusters': [
                {
                    'ClusterIdentifier': 'cluster-1',
                    'NodeType': 'ra3.4xlarge',
                    'NumberOfNodes': 4,
                    'ClusterStatus': 'available',
                    'ClusterCreateTime': datetime(2024, 1, 1, 12, 0, 0),
                    'AvailabilityZone': 'us-east-2a',
                    'Encrypted': True,
                    'PubliclyAccessible': False,
                },
                {
                    'ClusterIdentifier': 'cluster-2',
                    'NodeType': 'dc2.large',
                    'NumberOfNodes': 2,
                    'ClusterStatus': 'available',
                    'ClusterCreateTime': datetime(2024, 1, 2, 12, 0, 0),
                    'AvailabilityZone': 'us-east-2b',
                    'Encrypted': False,
                    'PubliclyAccessible': True,
                }
            ]
        }
        mock_boto3.return_value = mock_client
        
        # Call the function
        result = list_redshift_clusters('us-east-2')
        
        # Assertions
        assert len(result) == 2
        assert result[0]['cluster_identifier'] == 'cluster-1'
        assert result[0]['node_type'] == 'ra3.4xlarge'
        assert result[0]['encrypted'] == True
        assert result[1]['cluster_identifier'] == 'cluster-2'
        assert result[1]['node_type'] == 'dc2.large'
        assert result[1]['publicly_accessible'] == True
    
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_list_no_clusters(self, mock_boto3):
        """Test listing when no clusters exist."""
        # Mock AWS response with no clusters
        mock_client = Mock()
        mock_client.describe_clusters.return_value = {'Clusters': []}
        mock_boto3.return_value = mock_client
        
        # Call the function
        result = list_redshift_clusters('us-east-2')
        
        # Assertions
        assert len(result) == 0
        assert result == []
    
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_list_clusters_error(self, mock_boto3):
        """Test error handling when listing clusters returns a dict with error key."""
        # Mock AWS error
        mock_client = Mock()
        mock_client.describe_clusters.side_effect = Exception('AccessDenied')
        mock_boto3.return_value = mock_client
        
        # Call the function
        result = list_redshift_clusters('us-east-2')
        
        # Assertions — error returns a single dict, not a list
        assert isinstance(result, dict)
        assert 'error' in result
        assert result['region'] == 'us-east-2'


class TestGetWlmConfiguration:
    """Test the get_wlm_configuration function."""

    @patch('redshift_agents.tools.redshift_tools.time.sleep')
    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_successful_wlm_query(self, mock_boto3, mock_audit, mock_sleep):
        """Test successful WLM configuration retrieval."""
        mock_client = Mock()
        mock_client.execute_statement.return_value = {'Id': 'stmt-123'}
        mock_client.describe_statement.return_value = {'Status': 'FINISHED'}
        mock_client.get_statement_result.return_value = {
            'Records': [
                [
                    {'stringValue': 'etl_queue'},
                    {'longValue': 6},
                    {'longValue': 5},
                    {'longValue': 0},
                    {'longValue': 0},
                    {'longValue': 0},
                    {'doubleValue': 0.0},
                    {'longValue': 0},
                    {'doubleValue': 0.0},
                    {'doubleValue': 0.0},
                ],
                [
                    {'stringValue': 'analytics_queue'},
                    {'longValue': 7},
                    {'longValue': 10},
                    {'longValue': 0},
                    {'longValue': 0},
                    {'longValue': 0},
                    {'doubleValue': 0.0},
                    {'longValue': 0},
                    {'doubleValue': 0.0},
                    {'doubleValue': 0.0},
                ],
            ]
        }
        mock_boto3.return_value = mock_client

        result = get_wlm_configuration('test-cluster', 'us-east-2', user_id='jane.doe')

        assert 'error' not in result
        assert result['cluster_id'] == 'test-cluster'
        assert result['region'] == 'us-east-2'
        assert len(result['wlm_queues']) == 2
        assert result['wlm_queues'][0]['queue_name'] == 'etl_queue'
        assert result['wlm_queues'][0]['service_class'] == 6
        assert result['wlm_queues'][0]['concurrency'] == 5
        assert result['wlm_queues'][1]['queue_name'] == 'analytics_queue'
        assert result['wlm_queues'][1]['service_class'] == 7
        assert result['wlm_queues'][1]['concurrency'] == 10

        # Verify Redshift Data API was called with DbUser for identity propagation
        mock_client.execute_statement.assert_called_once()
        call_kwargs = mock_client.execute_statement.call_args[1]
        assert call_kwargs['ClusterIdentifier'] == 'test-cluster'
        assert call_kwargs['Database'] == 'dev'
        assert call_kwargs['DbUser'] == 'jane.doe'

        # Verify audit event
        mock_audit.assert_called_once_with(
            "tool_invocation",
            "assessment",
            initiated_by='jane.doe',
            cluster_id='test-cluster',
            region='us-east-2',
            details={"tool": "get_wlm_configuration"},
        )

    @patch('redshift_agents.tools.redshift_tools.time.sleep')
    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_query_failed(self, mock_boto3, mock_audit, mock_sleep):
        """Test handling when the Redshift Data API query fails."""
        mock_client = Mock()
        mock_client.execute_statement.return_value = {'Id': 'stmt-456'}
        mock_client.describe_statement.return_value = {
            'Status': 'FAILED',
            'Error': 'Permission denied',
        }
        mock_boto3.return_value = mock_client

        result = get_wlm_configuration('test-cluster', 'us-east-2', user_id='jane.doe')

        assert 'error' in result
        assert result['error'] == 'Permission denied'
        assert result['cluster_id'] == 'test-cluster'

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_exception_handling(self, mock_boto3, mock_audit):
        """Test handling of unexpected exceptions."""
        mock_client = Mock()
        mock_client.execute_statement.side_effect = Exception('Connection refused')
        mock_boto3.return_value = mock_client

        result = get_wlm_configuration('test-cluster', 'us-east-2', user_id='jane.doe')

        assert 'error' in result
        assert 'Connection refused' in result['error']
        assert result['cluster_id'] == 'test-cluster'
        assert result['region'] == 'us-east-2'

    @patch('redshift_agents.tools.redshift_tools.time.sleep')
    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_empty_results(self, mock_boto3, mock_audit, mock_sleep):
        """Test handling when no WLM queues are returned."""
        mock_client = Mock()
        mock_client.execute_statement.return_value = {'Id': 'stmt-789'}
        mock_client.describe_statement.return_value = {'Status': 'FINISHED'}
        mock_client.get_statement_result.return_value = {'Records': []}
        mock_boto3.return_value = mock_client

        result = get_wlm_configuration('test-cluster', 'us-east-2', user_id='jane.doe')

        assert 'error' not in result
        assert result['wlm_queues'] == []


class TestExecuteRedshiftQuery:
    """Test the execute_redshift_query function."""

    @patch('redshift_agents.tools.redshift_tools.time.sleep')
    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_successful_query_execution(self, mock_boto3, mock_audit, mock_sleep):
        """Test successful query execution via Redshift Data API."""
        mock_client = Mock()
        mock_client.execute_statement.return_value = {'Id': 'stmt-exec-1'}
        mock_client.describe_statement.return_value = {'Status': 'FINISHED'}
        mock_client.get_statement_result.return_value = {
            'Records': [
                [{'stringValue': 'row1_col1'}, {'longValue': 42}],
                [{'stringValue': 'row2_col1'}, {'longValue': 99}],
            ]
        }
        mock_boto3.return_value = mock_client

        result = execute_redshift_query(
            'test-cluster', 'SELECT * FROM my_table', 'us-east-2', user_id='jane.doe'
        )

        assert 'error' not in result
        assert result['cluster_id'] == 'test-cluster'
        assert result['region'] == 'us-east-2'
        assert len(result['records']) == 2

        # Verify Redshift Data API was called with DbUser for identity propagation
        mock_client.execute_statement.assert_called_once()
        call_kwargs = mock_client.execute_statement.call_args[1]
        assert call_kwargs['ClusterIdentifier'] == 'test-cluster'
        assert call_kwargs['Database'] == 'dev'
        assert call_kwargs['DbUser'] == 'jane.doe'
        assert call_kwargs['Sql'] == 'SELECT * FROM my_table'

        # Verify audit event was emitted with user_id and query in details
        mock_audit.assert_called_once_with(
            "tool_invocation",
            "execution",
            initiated_by='jane.doe',
            cluster_id='test-cluster',
            region='us-east-2',
            details={"tool": "execute_redshift_query", "query": "SELECT * FROM my_table"},
        )

    @patch('redshift_agents.tools.redshift_tools.time.sleep')
    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_query_failure(self, mock_boto3, mock_audit, mock_sleep):
        """Test handling when the Redshift Data API query fails."""
        mock_client = Mock()
        mock_client.execute_statement.return_value = {'Id': 'stmt-exec-2'}
        mock_client.describe_statement.return_value = {
            'Status': 'FAILED',
            'Error': 'Syntax error in SQL',
        }
        mock_boto3.return_value = mock_client

        result = execute_redshift_query(
            'test-cluster', 'INVALID SQL', 'us-east-2', user_id='jane.doe'
        )

        assert 'error' in result
        assert result['error'] == 'Syntax error in SQL'
        assert result['cluster_id'] == 'test-cluster'
        assert result['region'] == 'us-east-2'

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_exception_handling(self, mock_boto3, mock_audit):
        """Test handling of unexpected exceptions."""
        mock_client = Mock()
        mock_client.execute_statement.side_effect = Exception('Connection refused')
        mock_boto3.return_value = mock_client

        result = execute_redshift_query(
            'test-cluster', 'SELECT 1', 'us-east-2', user_id='jane.doe'
        )

        assert 'error' in result
        assert 'Connection refused' in result['error']
        assert result['cluster_id'] == 'test-cluster'
        assert result['region'] == 'us-east-2'


class TestCreateServerlessNamespace:
    """Test the create_serverless_namespace function."""

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_successful_namespace_creation(self, mock_boto3, mock_audit):
        """Test successful Serverless namespace creation."""
        mock_client = Mock()
        mock_client.create_namespace.return_value = {
            'namespace': {
                'namespaceName': 'my-namespace',
                'namespaceId': 'ns-abc123',
                'namespaceArn': 'arn:aws:redshift-serverless:us-east-2:XXXXXXXXXXXX:namespace/ns-abc123',
                'status': 'AVAILABLE',
                'adminUsername': 'admin',
                'dbName': 'dev',
            }
        }
        mock_boto3.return_value = mock_client

        result = create_serverless_namespace(
            'my-namespace', admin_username='admin', db_name='dev',
            region='us-east-2', user_id='jane.doe',
        )

        assert result['namespace_name'] == 'my-namespace'
        assert result['namespace_id'] == 'ns-abc123'
        assert result['status'] == 'AVAILABLE'
        assert result['admin_username'] == 'admin'
        assert result['db_name'] == 'dev'
        assert result['region'] == 'us-east-2'
        assert 'error' not in result

        mock_boto3.assert_called_once_with('redshift-serverless', region_name='us-east-2')
        mock_client.create_namespace.assert_called_once_with(
            namespaceName='my-namespace',
            adminUsername='admin',
            dbName='dev',
        )

        mock_audit.assert_called_once_with(
            "tool_invocation",
            "execution",
            initiated_by='jane.doe',
            region='us-east-2',
            details={"tool": "create_serverless_namespace"},
        )

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_namespace_creation_error(self, mock_boto3, mock_audit):
        """Test error handling when namespace creation fails."""
        mock_client = Mock()
        mock_client.create_namespace.side_effect = Exception('ConflictException: Namespace already exists')
        mock_boto3.return_value = mock_client

        result = create_serverless_namespace(
            'my-namespace', region='us-east-2', user_id='jane.doe',
        )

        assert 'error' in result
        assert 'ConflictException' in result['error']
        assert result['namespace_name'] == 'my-namespace'
        assert result['region'] == 'us-east-2'


class TestCreateServerlessWorkgroup:
    """Test the create_serverless_workgroup function."""

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_successful_workgroup_creation(self, mock_boto3, mock_audit):
        """Test successful Serverless workgroup creation."""
        mock_client = Mock()
        mock_client.create_workgroup.return_value = {
            'workgroup': {
                'workgroupName': 'my-workgroup',
                'workgroupId': 'wg-abc123',
                'workgroupArn': 'arn:aws:redshift-serverless:us-east-2:XXXXXXXXXXXX:workgroup/wg-abc123',
                'status': 'AVAILABLE',
                'namespaceName': 'my-namespace',
                'baseCapacity': 32,
                'maxCapacity': 512,
            }
        }
        mock_boto3.return_value = mock_client

        result = create_serverless_workgroup(
            'my-workgroup', 'my-namespace', base_rpu=32, max_rpu=512,
            region='us-east-2', user_id='jane.doe',
        )

        assert result['workgroup_name'] == 'my-workgroup'
        assert result['workgroup_id'] == 'wg-abc123'
        assert result['status'] == 'AVAILABLE'
        assert result['namespace_name'] == 'my-namespace'
        assert result['base_capacity'] == 32
        assert result['max_capacity'] == 512
        assert result['region'] == 'us-east-2'
        assert 'error' not in result

        mock_boto3.assert_called_once_with('redshift-serverless', region_name='us-east-2')
        mock_client.create_workgroup.assert_called_once_with(
            workgroupName='my-workgroup',
            namespaceName='my-namespace',
            baseCapacity=32,
            maxCapacity=512,
        )

        mock_audit.assert_called_once_with(
            "tool_invocation",
            "execution",
            initiated_by='jane.doe',
            region='us-east-2',
            details={"tool": "create_serverless_workgroup"},
        )

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_workgroup_creation_error(self, mock_boto3, mock_audit):
        """Test error handling when workgroup creation fails."""
        mock_client = Mock()
        mock_client.create_workgroup.side_effect = Exception('ConflictException: Workgroup already exists')
        mock_boto3.return_value = mock_client

        result = create_serverless_workgroup(
            'my-workgroup', 'my-namespace', region='us-east-2', user_id='jane.doe',
        )

        assert 'error' in result
        assert 'ConflictException' in result['error']
        assert result['workgroup_name'] == 'my-workgroup'
        assert result['region'] == 'us-east-2'


class TestRestoreSnapshotToServerless:
    """Test the restore_snapshot_to_serverless function."""

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_successful_restore(self, mock_boto3, mock_audit):
        """Test successful snapshot restore to Serverless namespace."""
        mock_client = Mock()
        mock_client.restore_from_snapshot.return_value = {
            'namespace': {
                'namespaceName': 'my-namespace',
                'namespaceId': 'ns-restore123',
                'namespaceArn': 'arn:aws:redshift-serverless:us-east-2:XXXXXXXXXXXX:namespace/ns-restore123',
                'status': 'RESTORING',
            }
        }
        mock_boto3.return_value = mock_client

        result = restore_snapshot_to_serverless(
            'my-snapshot', 'my-namespace', region='us-east-2', user_id='jane.doe',
        )

        assert result['namespace_name'] == 'my-namespace'
        assert result['namespace_id'] == 'ns-restore123'
        assert result['status'] == 'RESTORING'
        assert result['snapshot_identifier'] == 'my-snapshot'
        assert result['region'] == 'us-east-2'
        assert 'error' not in result

        mock_boto3.assert_called_once_with('redshift-serverless', region_name='us-east-2')
        mock_client.restore_from_snapshot.assert_called_once_with(
            namespaceName='my-namespace',
            snapshotName='my-snapshot',
        )

        mock_audit.assert_called_once_with(
            "tool_invocation",
            "execution",
            initiated_by='jane.doe',
            region='us-east-2',
            details={"tool": "restore_snapshot_to_serverless"},
        )

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_restore_error(self, mock_boto3, mock_audit):
        """Test error handling when snapshot restore fails."""
        mock_client = Mock()
        mock_client.restore_from_snapshot.side_effect = Exception('SnapshotNotFound: Snapshot does not exist')
        mock_boto3.return_value = mock_client

        result = restore_snapshot_to_serverless(
            'bad-snapshot', 'my-namespace', region='us-east-2', user_id='jane.doe',
        )

        assert 'error' in result
        assert 'SnapshotNotFound' in result['error']
        assert result['snapshot_identifier'] == 'bad-snapshot'
        assert result['namespace_name'] == 'my-namespace'
        assert result['region'] == 'us-east-2'


class TestSetupDataSharing:
    """Test the setup_data_sharing function."""

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_successful_data_sharing_setup(self, mock_boto3, mock_audit):
        """Test successful data sharing setup between producer and consumers."""
        mock_serverless = Mock()
        mock_data = Mock()

        # get_namespace responses for producer and consumers
        mock_serverless.get_namespace.side_effect = [
            {'namespace': {'namespaceName': 'producer-ns', 'namespaceId': 'ns-prod-001'}},
            {'namespace': {'namespaceName': 'consumer-ns-1', 'namespaceId': 'ns-con-001'}},
            {'namespace': {'namespaceName': 'consumer-ns-2', 'namespaceId': 'ns-con-002'}},
        ]

        mock_data.execute_statement.return_value = {'Id': 'stmt-ds-1'}

        def route_client(service, **kwargs):
            if service == 'redshift-serverless':
                return mock_serverless
            return mock_data

        mock_boto3.side_effect = route_client

        result = setup_data_sharing(
            'producer-ns', 'consumer-ns-1, consumer-ns-2',
            datashare_name='my_share', region='us-east-2', user_id='jane.doe',
        )

        assert 'error' not in result
        assert result['datashare_name'] == 'my_share'
        assert result['producer_namespace'] == 'producer-ns'
        assert result['producer_namespace_id'] == 'ns-prod-001'
        assert len(result['consumer_namespaces']) == 2
        assert result['consumer_namespaces'][0]['name'] == 'consumer-ns-1'
        assert result['consumer_namespaces'][0]['namespace_id'] == 'ns-con-001'
        assert result['consumer_namespaces'][1]['name'] == 'consumer-ns-2'
        assert result['consumer_namespaces'][1]['namespace_id'] == 'ns-con-002'
        # 3 base SQL + 2 GRANT statements = 5
        assert result['statements_executed'] == 5
        assert result['region'] == 'us-east-2'

        mock_audit.assert_called_once_with(
            "tool_invocation",
            "execution",
            initiated_by='jane.doe',
            region='us-east-2',
            details={"tool": "setup_data_sharing"},
        )

    @patch('redshift_agents.tools.redshift_tools.emit_audit_event')
    @patch('redshift_agents.tools.redshift_tools.boto3.client')
    def test_data_sharing_error_handling(self, mock_boto3, mock_audit):
        """Test error handling when data sharing setup fails."""
        mock_serverless = Mock()
        mock_serverless.get_namespace.side_effect = Exception('NamespaceNotFound: producer-ns not found')

        mock_boto3.return_value = mock_serverless

        result = setup_data_sharing(
            'producer-ns', 'consumer-ns-1',
            region='us-east-2', user_id='jane.doe',
        )

        assert 'error' in result
        assert 'NamespaceNotFound' in result['error']
        assert result['producer_namespace'] == 'producer-ns'
        assert result['region'] == 'us-east-2'


# ---------------------------------------------------------------------------
# Property-based tests for Redshift tools
# ---------------------------------------------------------------------------
from hypothesis import given, settings, strategies as st

# --- Strategies for Property 1 ---

# Generate valid AWS-style cluster identifiers (lowercase alphanumeric + hyphens)
_cluster_id_st = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",
    min_size=1,
    max_size=30,
).filter(lambda s: not s.startswith("-") and not s.endswith("-"))

_node_types = ["ra3.xlplus", "ra3.4xlarge", "ra3.16xlarge", "dc2.large", "dc2.8xlarge", "ds2.xlarge"]

_cluster_st = st.fixed_dictionaries({
    "ClusterIdentifier": _cluster_id_st,
    "NodeType": st.sampled_from(_node_types),
    "NumberOfNodes": st.integers(min_value=1, max_value=128),
    "ClusterStatus": st.sampled_from(["available", "creating", "deleting", "modifying"]),
    "ClusterCreateTime": st.just("2024-01-01T00:00:00Z"),
    "AvailabilityZone": st.sampled_from(["us-east-2a", "us-east-2b", "us-west-2a", "eu-west-1a"]),
    "Encrypted": st.booleans(),
    "PubliclyAccessible": st.booleans(),
})

# Generate a list of clusters with unique identifiers
_clusters_st = st.lists(
    _cluster_st,
    min_size=0,
    max_size=20,
    unique_by=lambda c: c["ClusterIdentifier"],
)

_region_st = st.sampled_from([
    "us-east-1", "us-east-2", "us-west-2", "eu-west-1", "ap-southeast-1",
])


@settings(max_examples=100)
@given(clusters=_clusters_st, region=_region_st)
@patch("redshift_agents.tools.redshift_tools.emit_audit_event")
@patch("redshift_agents.tools.redshift_tools.boto3.client")
def test_cluster_listing_returns_all_clusters_in_region(
    mock_boto3,
    mock_audit,
    clusters,
    region,
):
    """Property 1: Cluster listing returns all clusters in region

    For any mocked set of Redshift clusters in a given region, calling
    list_redshift_clusters(region) should return a list whose length equals
    the number of clusters in the mock, and every cluster identifier from
    the mock should appear in the result.

    **Validates: Requirements FR-2.1**
    """
    # Feature: redshift-modernization-agents, Property 1: Cluster listing returns all clusters in region

    mock_client = Mock()
    mock_client.describe_clusters.return_value = {"Clusters": clusters}
    mock_boto3.return_value = mock_client

    result = list_redshift_clusters(region)

    # Result must be a list (not an error dict)
    assert isinstance(result, list), f"Expected list, got {type(result)}: {result}"

    # Length must match the number of mocked clusters
    assert len(result) == len(clusters), (
        f"Expected {len(clusters)} clusters, got {len(result)}"
    )

    # Every cluster identifier from the mock must appear in the result
    expected_ids = {c["ClusterIdentifier"] for c in clusters}
    actual_ids = {r["cluster_identifier"] for r in result}
    assert actual_ids == expected_ids, (
        f"Cluster IDs mismatch: expected {expected_ids}, got {actual_ids}"
    )


# Run tests with: pytest tests/test_redshift_tools.py -v


# --- Strategies for Property 2 ---

# Full cluster response dict as returned by describe_clusters for a single cluster
_full_cluster_st = st.fixed_dictionaries({
    "ClusterIdentifier": _cluster_id_st,
    "NodeType": st.sampled_from(_node_types),
    "NumberOfNodes": st.integers(min_value=1, max_value=128),
    "ClusterStatus": st.sampled_from(["available", "creating", "deleting", "modifying"]),
    "ClusterVersion": st.text(alphabet="0123456789.", min_size=1, max_size=5),
    "AvailabilityZone": st.sampled_from(["us-east-2a", "us-east-2b", "us-west-2a", "eu-west-1a"]),
    "Encrypted": st.booleans(),
    "KmsKeyId": st.text(min_size=0, max_size=20),
    "PubliclyAccessible": st.booleans(),
    "VpcId": st.from_regex(r"vpc-[a-f0-9]{8}", fullmatch=True),
    "VpcSecurityGroups": st.just([{"VpcSecurityGroupId": "sg-12345678"}]),
    "EnhancedVpcRouting": st.booleans(),
    "Endpoint": st.fixed_dictionaries({
        "Address": st.just("cluster.abc.us-east-2.redshift.amazonaws.com"),
        "Port": st.just(5439),
    }),
    "ClusterParameterGroups": st.just([{"ParameterGroupName": "default.redshift-1.0"}]),
    "AutomatedSnapshotRetentionPeriod": st.integers(min_value=0, max_value=35),
    "PreferredMaintenanceWindow": st.just("sun:05:00-sun:05:30"),
    "ClusterCreateTime": st.just("2024-01-01T00:00:00Z"),
    "MasterUsername": st.just("admin"),
    "DBName": st.just("dev"),
})

_user_id_st = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789._-",
    min_size=1,
    max_size=20,
)


@settings(max_examples=100)
@given(cluster=_full_cluster_st, region=_region_st, user_id=_user_id_st)
@patch("redshift_agents.tools.redshift_tools.emit_audit_event")
@patch("redshift_agents.tools.redshift_tools.boto3.client")
def test_cluster_configuration_output_contains_all_required_fields(
    mock_boto3,
    mock_audit,
    cluster,
    region,
    user_id,
):
    """Property 2: Cluster configuration output contains all required fields

    For any Redshift cluster (mocked via describe_clusters), calling
    analyze_redshift_cluster(cluster_id, region, user_id) should return a dict
    containing all required keys: cluster_identifier, node_type,
    number_of_nodes, cluster_status, cluster_version, encrypted, vpc_id,
    publicly_accessible, enhanced_vpc_routing.

    **Validates: Requirements FR-2.2**
    """
    # Feature: redshift-modernization-agents, Property 2: Cluster configuration output contains all required fields

    mock_client = Mock()
    mock_client.describe_clusters.return_value = {"Clusters": [cluster]}
    mock_boto3.return_value = mock_client

    result = analyze_redshift_cluster(
        cluster["ClusterIdentifier"], region, user_id=user_id
    )

    # Result must be a dict without an error key (successful call)
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "error" not in result, f"Unexpected error: {result.get('error')}"

    # All required keys must be present
    required_keys = {
        "cluster_identifier",
        "node_type",
        "number_of_nodes",
        "cluster_status",
        "cluster_version",
        "encrypted",
        "vpc_id",
        "publicly_accessible",
        "enhanced_vpc_routing",
    }
    missing = required_keys - result.keys()
    assert not missing, f"Missing required keys: {missing}"

    # Values must match the mocked cluster data
    assert result["cluster_identifier"] == cluster["ClusterIdentifier"]
    assert result["node_type"] == cluster["NodeType"]
    assert result["number_of_nodes"] == cluster["NumberOfNodes"]
    assert result["cluster_status"] == cluster["ClusterStatus"]
    assert result["cluster_version"] == cluster["ClusterVersion"]
    assert result["encrypted"] == cluster["Encrypted"]
    assert result["vpc_id"] == cluster["VpcId"]
    assert result["publicly_accessible"] == cluster["PubliclyAccessible"]
    assert result["enhanced_vpc_routing"] == cluster["EnhancedVpcRouting"]


# --- Strategies for Property 3 ---

# Generate a single CloudWatch datapoint with random metric values
_datapoint_st = st.fixed_dictionaries({
    "Timestamp": st.just(datetime(2024, 1, 1, 12, 0, 0)),
    "Average": st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    "Maximum": st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    "Minimum": st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
})

# Generate a non-empty list of datapoints (at least 1 so the metric has data)
_datapoints_st = st.lists(_datapoint_st, min_size=1, max_size=10)

_hours_st = st.integers(min_value=1, max_value=168)

REQUIRED_METRIC_CATEGORIES = [
    "CPUUtilization",
    "DatabaseConnections",
    "NetworkReceiveThroughput",
    "NetworkTransmitThroughput",
    "PercentageDiskSpaceUsed",
    "ReadLatency",
    "WriteLatency",
]


@settings(max_examples=100)
@given(
    cluster_id=_cluster_id_st,
    region=_region_st,
    user_id=_user_id_st,
    hours=_hours_st,
    datapoints=_datapoints_st,
)
@patch("redshift_agents.tools.redshift_tools.emit_audit_event")
@patch("redshift_agents.tools.redshift_tools.boto3.client")
def test_cloudwatch_metrics_output_contains_all_required_categories(
    mock_boto3,
    mock_audit,
    cluster_id,
    region,
    user_id,
    hours,
    datapoints,
):
    """Property 3: CloudWatch metrics output contains all required metric categories

    For any cluster with CloudWatch data, calling
    get_cluster_metrics(cluster_id, region, hours, user_id) should return a dict
    whose `metrics` key contains entries for all required categories:
    CPUUtilization, DatabaseConnections, NetworkReceiveThroughput,
    NetworkTransmitThroughput, PercentageDiskSpaceUsed, ReadLatency,
    WriteLatency.

    **Validates: Requirements FR-2.3**
    """
    # Feature: redshift-modernization-agents, Property 3: CloudWatch metrics output contains all required metric categories

    mock_client = Mock()
    mock_client.get_metric_statistics.return_value = {"Datapoints": datapoints}
    mock_boto3.return_value = mock_client

    result = get_cluster_metrics(cluster_id, region, hours=hours, user_id=user_id)

    # Result must be a dict without an error key (successful call)
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "error" not in result, f"Unexpected error: {result.get('error')}"

    # The result must contain a 'metrics' key
    assert "metrics" in result, "Result missing 'metrics' key"

    metrics = result["metrics"]

    # All 7 required metric categories must be present
    missing = set(REQUIRED_METRIC_CATEGORIES) - set(metrics.keys())
    assert not missing, f"Missing required metric categories: {missing}"

    # Each metric entry should have summary statistics (since we provided datapoints)
    for category in REQUIRED_METRIC_CATEGORIES:
        entry = metrics[category]
        assert "average" in entry, f"{category} missing 'average'"
        assert "maximum" in entry, f"{category} missing 'maximum'"
        assert "minimum" in entry, f"{category} missing 'minimum'"
        assert "datapoint_count" in entry, f"{category} missing 'datapoint_count'"


# --- Strategies for Property 4 ---

# Generate a single WLM queue record as the Redshift Data API would return it
_queue_name_st = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
    min_size=1,
    max_size=20,
)

_wlm_record_st = st.tuples(
    _queue_name_st,                                                          # queue_name
    st.integers(min_value=5, max_value=20),                                  # service_class
    st.integers(min_value=1, max_value=50),                                  # concurrency
    st.integers(min_value=0, max_value=500),                                 # queries_waiting
    st.integers(min_value=0, max_value=60000),                               # avg_wait_time_ms
    st.integers(min_value=0, max_value=120000),                              # avg_exec_time_ms
    st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),  # wait_to_exec_ratio
    st.integers(min_value=0, max_value=1000),                                # queries_spilling_to_disk
    st.floats(min_value=0.0, max_value=50000.0, allow_nan=False, allow_infinity=False),  # disk_spill_mb
    st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),    # saturation_pct
)

# Generate a list of 1+ WLM queue records
_wlm_records_st = st.lists(_wlm_record_st, min_size=1, max_size=15)


def _wlm_tuple_to_data_api_row(record):
    """Convert a generated WLM tuple into a Redshift Data API Records row."""
    (
        queue_name, service_class, concurrency, queries_waiting,
        avg_wait_time_ms, avg_exec_time_ms, wait_to_exec_ratio,
        queries_spilling_to_disk, disk_spill_mb, saturation_pct,
    ) = record
    return [
        {"stringValue": queue_name},
        {"longValue": service_class},
        {"longValue": concurrency},
        {"longValue": queries_waiting},
        {"longValue": avg_wait_time_ms},
        {"longValue": avg_exec_time_ms},
        {"doubleValue": wait_to_exec_ratio},
        {"longValue": queries_spilling_to_disk},
        {"doubleValue": disk_spill_mb},
        {"doubleValue": saturation_pct},
    ]


@settings(max_examples=100)
@given(
    wlm_records=_wlm_records_st,
    cluster_id=_cluster_id_st,
    region=_region_st,
    user_id=_user_id_st,
)
@patch("redshift_agents.tools.redshift_tools.time.sleep")
@patch("redshift_agents.tools.redshift_tools.emit_audit_event")
@patch("redshift_agents.tools.redshift_tools.boto3.client")
def test_wlm_per_queue_metrics_are_complete(
    mock_boto3,
    mock_audit,
    mock_sleep,
    wlm_records,
    cluster_id,
    region,
    user_id,
):
    """Property 4: WLM per-queue metrics are complete

    For any WLM configuration with N queues (N >= 1), the output's
    wlm_queues should contain exactly N entries, and each entry should
    include all required fields: queue_name, service_class, concurrency,
    queries_waiting, avg_wait_time_ms, avg_exec_time_ms,
    wait_to_exec_ratio, queries_spilling_to_disk, disk_spill_mb,
    saturation_pct.

    **Validates: Requirements FR-2.4, FR-2.5**
    """
    # Feature: redshift-modernization-agents, Property 4: WLM per-queue metrics are complete

    # Build Data API mock records from generated tuples
    api_records = [_wlm_tuple_to_data_api_row(r) for r in wlm_records]

    mock_client = Mock()
    mock_client.execute_statement.return_value = {"Id": "stmt-prop4"}
    mock_client.describe_statement.return_value = {"Status": "FINISHED"}
    mock_client.get_statement_result.return_value = {"Records": api_records}
    mock_boto3.return_value = mock_client

    result = get_wlm_configuration(cluster_id, region, user_id=user_id)

    # Result must be a dict without an error key
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "error" not in result, f"Unexpected error: {result.get('error')}"

    # Must contain wlm_queues key
    assert "wlm_queues" in result, "Result missing 'wlm_queues' key"

    queues = result["wlm_queues"]

    # Exactly N entries
    assert len(queues) == len(wlm_records), (
        f"Expected {len(wlm_records)} queues, got {len(queues)}"
    )

    # Each entry must have all 10 required fields
    required_fields = {
        "queue_name",
        "service_class",
        "concurrency",
        "queries_waiting",
        "avg_wait_time_ms",
        "avg_exec_time_ms",
        "wait_to_exec_ratio",
        "queries_spilling_to_disk",
        "disk_spill_mb",
        "saturation_pct",
    }

    for i, queue in enumerate(queues):
        missing = required_fields - set(queue.keys())
        assert not missing, (
            f"Queue {i} missing required fields: {missing}"
        )


# --- Strategy for Property 13 ---

# Generate non-empty SQL query strings
_query_st = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _*.,;()=<>",
    min_size=1,
    max_size=200,
)


@settings(max_examples=100)
@given(
    cluster_id=_cluster_id_st,
    region=_region_st,
    user_id=_user_id_st,
    query=_query_st,
)
@patch("redshift_agents.tools.redshift_tools.time.sleep")
@patch("redshift_agents.tools.redshift_tools.emit_audit_event")
@patch("redshift_agents.tools.redshift_tools.boto3.client")
def test_identity_propagation_consistency(
    mock_boto3,
    mock_audit,
    mock_sleep,
    cluster_id,
    region,
    user_id,
    query,
):
    """Property 13: Identity propagation consistency

    For any tool invocation with a user_id parameter, the emitted audit
    event's initiated_by field must equal user_id, and any
    execute_redshift_query call must pass DbUser=user_id to the Redshift
    Data API.

    **Validates: Requirements FR-5.3, NFR-7.1, NFR-7.3**
    """
    # Feature: redshift-modernization-agents, Property 13: Identity propagation consistency

    mock_client = Mock()
    mock_client.execute_statement.return_value = {"Id": "stmt-prop13"}
    mock_client.describe_statement.return_value = {"Status": "FINISHED"}
    mock_client.get_statement_result.return_value = {"Records": []}
    mock_boto3.return_value = mock_client

    result = execute_redshift_query(cluster_id, query, region, user_id=user_id)

    # Result must be a dict without an error key (successful call)
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "error" not in result, f"Unexpected error: {result.get('error')}"

    # (1) emit_audit_event must have been called with initiated_by=user_id
    mock_audit.assert_called_once()
    audit_kwargs = mock_audit.call_args
    assert audit_kwargs[1]["initiated_by"] == user_id, (
        f"Audit initiated_by mismatch: expected {user_id!r}, "
        f"got {audit_kwargs[1].get('initiated_by')!r}"
    )

    # (2) execute_statement must have been called with DbUser=user_id
    mock_client.execute_statement.assert_called_once()
    exec_kwargs = mock_client.execute_statement.call_args[1]
    assert exec_kwargs["DbUser"] == user_id, (
        f"DbUser mismatch: expected {user_id!r}, got {exec_kwargs.get('DbUser')!r}"
    )


# --- Property 18: Tools pass region parameter to boto3 client ---


@settings(max_examples=100)
@given(
    cluster_id=_cluster_id_st,
    region=_region_st,
    user_id=_user_id_st,
)
@patch("redshift_agents.tools.redshift_tools.emit_audit_event")
@patch("redshift_agents.tools.redshift_tools.boto3.client")
def test_tools_pass_region_parameter_to_boto3_client(
    mock_boto3,
    mock_audit,
    cluster_id,
    region,
    user_id,
):
    """Property 18: Tools pass region parameter to boto3 client

    For any tool invocation with a region parameter, the boto3 client must
    be created with region_name equal to the specified region, not a
    hardcoded default.

    **Validates: Requirements NFR-3.3**
    """
    # Feature: redshift-modernization-agents, Property 18: Tools pass region parameter to boto3 client

    # Set up a mock client that returns valid responses for all tools
    mock_client = Mock()

    # list_redshift_clusters response
    mock_client.describe_clusters.return_value = {"Clusters": []}

    # get_cluster_metrics response (CloudWatch)
    mock_client.get_metric_statistics.return_value = {"Datapoints": []}

    mock_boto3.return_value = mock_client

    # --- Tool 1: list_redshift_clusters ---
    mock_boto3.reset_mock()
    list_redshift_clusters(region, user_id=user_id)
    mock_boto3.assert_called_with("redshift", region_name=region)

    # --- Tool 2: analyze_redshift_cluster ---
    mock_boto3.reset_mock()
    mock_client.describe_clusters.return_value = {
        "Clusters": [{
            "ClusterIdentifier": cluster_id,
            "NodeType": "ra3.4xlarge",
            "NumberOfNodes": 2,
            "ClusterStatus": "available",
            "ClusterVersion": "1.0",
            "AvailabilityZone": "us-east-2a",
            "Encrypted": False,
            "PubliclyAccessible": False,
            "VpcId": "vpc-00000000",
            "VpcSecurityGroups": [],
            "EnhancedVpcRouting": False,
            "Endpoint": {"Address": "x.amazonaws.com", "Port": 5439},
            "ClusterParameterGroups": [{"ParameterGroupName": "default"}],
            "AutomatedSnapshotRetentionPeriod": 1,
            "PreferredMaintenanceWindow": "sun:05:00-sun:05:30",
            "ClusterCreateTime": "2024-01-01T00:00:00Z",
            "MasterUsername": "admin",
            "DBName": "dev",
        }]
    }
    analyze_redshift_cluster(cluster_id, region, user_id=user_id)
    mock_boto3.assert_called_with("redshift", region_name=region)

    # --- Tool 3: get_cluster_metrics ---
    mock_boto3.reset_mock()
    get_cluster_metrics(cluster_id, region, user_id=user_id)
    mock_boto3.assert_called_with("cloudwatch", region_name=region)
