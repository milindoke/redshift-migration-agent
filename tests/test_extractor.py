"""Tests for provisioned cluster extractor."""

import pytest
from unittest.mock import Mock, patch
from redshift_migrate.extractors import ProvisionedClusterExtractor


@pytest.fixture
def mock_cluster_response():
    """Mock cluster response from AWS."""
    return {
        "Clusters": [
            {
                "ClusterIdentifier": "test-cluster",
                "VpcId": "vpc-12345",
                "PubliclyAccessible": False,
                "IamRoles": [
                    {"IamRoleArn": "arn:aws:iam::123456789012:role/RedshiftRole1"},
                    {"IamRoleArn": "arn:aws:iam::123456789012:role/RedshiftRole2"},
                ],
                "DefaultIamRoleArn": "arn:aws:iam::123456789012:role/RedshiftRole1",
                "VpcSecurityGroups": [
                    {"VpcSecurityGroupId": "sg-12345"},
                ],
                "ClusterSubnetGroupName": "test-subnet-group",
                "PreferredMaintenanceWindow": "sun:05:00-sun:05:30",
            }
        ]
    }


@pytest.fixture
def mock_subnet_group_response():
    """Mock subnet group response."""
    return {
        "ClusterSubnetGroups": [
            {
                "Subnets": [
                    {"SubnetIdentifier": "subnet-1"},
                    {"SubnetIdentifier": "subnet-2"},
                ]
            }
        ]
    }


def test_extract_cluster_basic(mock_cluster_response, mock_subnet_group_response):
    """Test basic cluster extraction."""
    with patch("boto3.client") as mock_client:
        mock_redshift = Mock()
        mock_redshift.describe_clusters.return_value = mock_cluster_response
        mock_redshift.describe_cluster_subnet_groups.return_value = mock_subnet_group_response
        mock_redshift.describe_snapshot_schedules.return_value = {"SnapshotSchedules": []}
        
        mock_client.return_value = mock_redshift
        
        extractor = ProvisionedClusterExtractor()
        config = extractor.extract("test-cluster")
        
        assert config.cluster_identifier == "test-cluster"
        assert len(config.iam_roles) == 2
        assert config.iam_roles[0].is_default is True
        assert config.vpc_config.vpc_id == "vpc-12345"
        assert len(config.vpc_config.subnet_ids) == 2


def test_extract_iam_roles(mock_cluster_response):
    """Test IAM role extraction."""
    with patch("boto3.client") as mock_client:
        mock_redshift = Mock()
        mock_redshift.describe_clusters.return_value = mock_cluster_response
        
        extractor = ProvisionedClusterExtractor()
        cluster = mock_cluster_response["Clusters"][0]
        roles = extractor._extract_iam_roles(cluster)
        
        assert len(roles) == 2
        assert roles[0].is_default is True
        assert roles[1].is_default is False
