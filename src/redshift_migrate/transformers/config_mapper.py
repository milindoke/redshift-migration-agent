"""Transform provisioned cluster config to serverless workgroup config."""

from typing import List, Dict
from ..models import ProvisionedClusterConfig, ServerlessWorkgroupConfig
from ..extractors.parameter_groups import ParameterGroupExtractor


class ConfigMapper:
    """Map provisioned cluster configuration to serverless workgroup."""

    def __init__(self):
        self.param_extractor = ParameterGroupExtractor()

    def transform(
        self,
        provisioned_config: ProvisionedClusterConfig,
        workgroup_name: str,
        namespace_name: str,
    ) -> ServerlessWorkgroupConfig:
        """Transform provisioned config to serverless config."""
        
        return ServerlessWorkgroupConfig(
            workgroup_name=workgroup_name,
            namespace_name=namespace_name,
            iam_roles=self._map_iam_roles(provisioned_config),
            subnet_ids=provisioned_config.vpc_config.subnet_ids,
            security_group_ids=provisioned_config.vpc_config.security_group_ids,
            publicly_accessible=provisioned_config.vpc_config.publicly_accessible,
            config_parameters=self._map_parameters(provisioned_config),
            tags=provisioned_config.tags,
        )

    def _map_iam_roles(self, config: ProvisionedClusterConfig) -> List[str]:
        """Extract IAM role ARNs, with default role first."""
        roles = []
        
        # Add default role first
        for role in config.iam_roles:
            if role.is_default:
                roles.append(role.role_arn)
        
        # Add remaining roles
        for role in config.iam_roles:
            if not role.is_default:
                roles.append(role.role_arn)
        
        return roles

    def _map_parameters(self, config: ProvisionedClusterConfig) -> List[Dict[str, str]]:
        """Map parameter group settings to serverless config parameters."""
        if not config.parameter_group_info:
            return []
        
        # Use the parameter extractor to map parameters
        return self.param_extractor.map_to_serverless_config(
            config.parameter_group_info.parameters
        )
