"""Tests for parameter group extraction and mapping."""

import pytest
from unittest.mock import Mock, patch
from redshift_migrate.extractors.parameter_groups import ParameterGroupExtractor


@pytest.fixture
def mock_parameters_response():
    """Mock parameter group response from AWS."""
    return {
        "Parameters": [
            {
                "ParameterName": "enable_user_activity_logging",
                "ParameterValue": "true",
                "DataType": "boolean",
                "Description": "Enable user activity logging",
                "Source": "user",
                "IsModifiable": True,
            },
            {
                "ParameterName": "max_query_execution_time",
                "ParameterValue": "3600000",
                "DataType": "integer",
                "Description": "Maximum query execution time",
                "Source": "user",
                "IsModifiable": True,
            },
            {
                "ParameterName": "some_default_param",
                "ParameterValue": "default_value",
                "DataType": "string",
                "Description": "A default parameter",
                "Source": "engine-default",
                "IsModifiable": True,
            },
        ]
    }


@pytest.fixture
def mock_parameter_group_info():
    """Mock parameter group info response."""
    return {
        "ParameterGroups": [
            {
                "ParameterGroupName": "test-param-group",
                "ParameterGroupFamily": "redshift-1.0",
                "Description": "Test parameter group",
                "Tags": [
                    {"Key": "Environment", "Value": "Production"},
                ],
            }
        ]
    }


def test_extract_parameters(mock_parameters_response):
    """Test parameter extraction from parameter group."""
    with patch("boto3.client") as mock_client:
        mock_redshift = Mock()
        mock_redshift.describe_cluster_parameters.return_value = mock_parameters_response
        mock_client.return_value = mock_redshift
        
        extractor = ParameterGroupExtractor()
        parameters = extractor.extract_parameters("test-param-group")
        
        # Should only include non-default, mappable parameters
        assert len(parameters) == 2
        assert "enable_user_activity_logging" in parameters
        assert "max_query_execution_time" in parameters
        assert "some_default_param" not in parameters  # Default parameter excluded


def test_map_to_serverless_config():
    """Test mapping parameters to serverless config format."""
    extractor = ParameterGroupExtractor()
    
    parameters = {
        "enable_user_activity_logging": {
            "value": "true",
            "data_type": "boolean",
        },
        "max_query_execution_time": {
            "value": "3600000",
            "data_type": "integer",
        },
    }
    
    config_params = extractor.map_to_serverless_config(parameters)
    
    assert len(config_params) == 2
    assert config_params[0]["parameterKey"] == "enable_user_activity_logging"
    assert config_params[0]["parameterValue"] == "true"
    assert config_params[1]["parameterKey"] == "max_query_execution_time"
    assert config_params[1]["parameterValue"] == "3600000"


def test_validate_parameter_compatibility():
    """Test parameter compatibility validation."""
    extractor = ParameterGroupExtractor()
    
    parameters = {
        "enable_user_activity_logging": {"value": "true"},
        "some_unsupported_param": {"value": "value"},
    }
    
    result = extractor.validate_parameter_compatibility(parameters)
    
    assert "enable_user_activity_logging" in result["compatible"]
    assert "some_unsupported_param" in result["incompatible"]
    assert len(result["warnings"]) > 0


def test_get_parameter_group_info(mock_parameter_group_info):
    """Test getting parameter group metadata."""
    with patch("boto3.client") as mock_client:
        mock_redshift = Mock()
        mock_redshift.describe_cluster_parameter_groups.return_value = mock_parameter_group_info
        mock_client.return_value = mock_redshift
        
        extractor = ParameterGroupExtractor()
        info = extractor.get_parameter_group_info("test-param-group")
        
        assert info is not None
        assert info["name"] == "test-param-group"
        assert info["family"] == "redshift-1.0"
        assert "Environment" in info["tags"]
