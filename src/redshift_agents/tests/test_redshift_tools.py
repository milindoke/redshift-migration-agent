"""
Unit tests for Redshift tools.

These tests run locally without AWS credentials by mocking boto3 responses.
This is TRUE local testing - no AWS access needed!
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the tools we want to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.redshift_tools import (
    analyze_redshift_cluster,
    get_cluster_metrics,
    list_redshift_clusters,
)


class TestAnalyzeRedshiftCluster:
    """Test the analyze_redshift_cluster function."""
    
    @patch('tools.redshift_tools.boto3.client')
    def test_successful_analysis(self, mock_boto3):
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
        
        # Call the function
        result = analyze_redshift_cluster('test-cluster', 'us-east-2')
        
        # Assertions
        assert result['cluster_identifier'] == 'test-cluster'
        assert result['node_type'] == 'ra3.4xlarge'
        assert result['number_of_nodes'] == 4
        assert result['cluster_status'] == 'available'
        assert result['encrypted'] == True
        assert result['publicly_accessible'] == False
        assert result['enhanced_vpc_routing'] == True
        assert result['region'] == 'us-east-2'
        
        # Verify boto3 was called correctly
        mock_boto3.assert_called_once_with('redshift', region_name='us-east-2')
        mock_client.describe_clusters.assert_called_once_with(ClusterIdentifier='test-cluster')
    
    @patch('tools.redshift_tools.boto3.client')
    def test_cluster_not_found(self, mock_boto3):
        """Test handling of cluster not found error."""
        # Mock AWS error
        mock_client = Mock()
        mock_client.describe_clusters.side_effect = Exception('ClusterNotFound')
        mock_boto3.return_value = mock_client
        
        # Call the function
        result = analyze_redshift_cluster('nonexistent-cluster', 'us-east-2')
        
        # Assertions
        assert 'error' in result
        assert result['cluster_id'] == 'nonexistent-cluster'
        assert result['region'] == 'us-east-2'


class TestGetClusterMetrics:
    """Test the get_cluster_metrics function."""
    
    @patch('tools.redshift_tools.boto3.client')
    def test_successful_metrics_retrieval(self, mock_boto3):
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
        
        # Call the function
        result = get_cluster_metrics('test-cluster', 'us-east-2', hours=24)
        
        # Assertions
        assert result['cluster_id'] == 'test-cluster'
        assert result['region'] == 'us-east-2'
        assert result['time_range_hours'] == 24
        assert 'metrics' in result
        assert 'timestamp' in result
        
        # Verify CloudWatch was called for each metric
        assert mock_client.get_metric_statistics.call_count == 7  # 7 metrics
    
    @patch('tools.redshift_tools.boto3.client')
    def test_no_datapoints_available(self, mock_boto3):
        """Test handling when no metrics are available."""
        # Mock CloudWatch response with no datapoints
        mock_client = Mock()
        mock_client.get_metric_statistics.return_value = {'Datapoints': []}
        mock_boto3.return_value = mock_client
        
        # Call the function
        result = get_cluster_metrics('test-cluster', 'us-east-2', hours=1)
        
        # Assertions
        assert result['cluster_id'] == 'test-cluster'
        assert 'metrics' in result
        # All metrics should have 'error': 'No data available'
        for metric_name, metric_data in result['metrics'].items():
            assert metric_data['error'] == 'No data available'


class TestListRedshiftClusters:
    """Test the list_redshift_clusters function."""
    
    @patch('tools.redshift_tools.boto3.client')
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
    
    @patch('tools.redshift_tools.boto3.client')
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
    
    @patch('tools.redshift_tools.boto3.client')
    def test_list_clusters_error(self, mock_boto3):
        """Test error handling when listing clusters."""
        # Mock AWS error
        mock_client = Mock()
        mock_client.describe_clusters.side_effect = Exception('AccessDenied')
        mock_boto3.return_value = mock_client
        
        # Call the function
        result = list_redshift_clusters('us-east-2')
        
        # Assertions
        assert len(result) == 1
        assert 'error' in result[0]
        assert result[0]['region'] == 'us-east-2'


# Run tests with: pytest tests/test_redshift_tools.py -v
