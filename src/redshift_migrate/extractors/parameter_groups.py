"""Extract and process parameter group configurations."""

import boto3
from typing import Dict, List, Optional, Any


class ParameterGroupExtractor:
    """Extract parameter group settings from Redshift."""

    # Parameters that can be mapped from provisioned to serverless
    MAPPABLE_PARAMETERS = {
        "enable_user_activity_logging": "enable_user_activity_logging",
        "query_group": "query_group",
        "max_query_execution_time": "max_query_execution_time",
        "enable_case_sensitive_identifier": "enable_case_sensitive_identifier",
        "search_path": "search_path",
        "statement_timeout": "statement_timeout",
        "datestyle": "datestyle",
        "timezone": "timezone",
        "require_ssl": "require_ssl",
        "use_fips_ssl": "use_fips_ssl",
    }

    def __init__(self, region: Optional[str] = None):
        self.redshift = boto3.client("redshift", region_name=region)

    def extract_parameters(
        self, parameter_group_name: str
    ) -> Dict[str, Any]:
        """Extract parameter values from a parameter group."""
        if not parameter_group_name:
            return {}

        try:
            response = self.redshift.describe_cluster_parameters(
                ParameterGroupName=parameter_group_name
            )
            
            parameters = {}
            for param in response.get("Parameters", []):
                param_name = param.get("ParameterName")
                param_value = param.get("ParameterValue")
                
                # Only include mappable parameters with non-default values
                if (
                    param_name in self.MAPPABLE_PARAMETERS
                    and param_value
                    and param.get("Source") != "engine-default"
                ):
                    parameters[param_name] = {
                        "value": param_value,
                        "data_type": param.get("DataType"),
                        "description": param.get("Description"),
                        "is_modifiable": param.get("IsModifiable", True),
                    }
            
            return parameters
            
        except Exception as e:
            print(f"Warning: Could not extract parameters from {parameter_group_name}: {e}")
            return {}

    def get_parameter_group_info(
        self, parameter_group_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get parameter group metadata."""
        try:
            response = self.redshift.describe_cluster_parameter_groups(
                ParameterGroupName=parameter_group_name
            )
            
            groups = response.get("ParameterGroups", [])
            if groups:
                group = groups[0]
                return {
                    "name": group.get("ParameterGroupName"),
                    "family": group.get("ParameterGroupFamily"),
                    "description": group.get("Description"),
                    "tags": {
                        tag["Key"]: tag["Value"] 
                        for tag in group.get("Tags", [])
                    },
                }
            
        except Exception as e:
            print(f"Warning: Could not get parameter group info: {e}")
        
        return None

    def map_to_serverless_config(
        self, parameters: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Map provisioned parameters to serverless config format."""
        config_params = []
        
        for param_name, param_info in parameters.items():
            serverless_name = self.MAPPABLE_PARAMETERS.get(param_name)
            if serverless_name:
                config_params.append({
                    "parameterKey": serverless_name,
                    "parameterValue": str(param_info["value"]),
                })
        
        return config_params

    def validate_parameter_compatibility(
        self, parameters: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Validate which parameters can be migrated to serverless."""
        result = {
            "compatible": [],
            "incompatible": [],
            "warnings": [],
        }
        
        for param_name, param_info in parameters.items():
            if param_name in self.MAPPABLE_PARAMETERS:
                result["compatible"].append(param_name)
            else:
                result["incompatible"].append(param_name)
                result["warnings"].append(
                    f"Parameter '{param_name}' is not supported in Redshift Serverless"
                )
        
        return result
