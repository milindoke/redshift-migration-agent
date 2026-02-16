"""Apply configuration to Redshift Serverless workgroups."""

import boto3
from typing import Optional, Dict, Any, List
from ..models import ServerlessWorkgroupConfig, ScheduledQuery
from .scheduled_queries import ScheduledQueryApplier


class ServerlessWorkgroupApplier:
    """Apply configuration to a Redshift Serverless workgroup."""

    def __init__(self, region: Optional[str] = None, dry_run: bool = False):
        self.redshift_serverless = boto3.client("redshift-serverless", region_name=region)
        self.dry_run = dry_run
        self.query_applier = ScheduledQueryApplier(region=region, dry_run=dry_run)

    def apply(
        self,
        config: ServerlessWorkgroupConfig,
        scheduled_queries: Optional[List[ScheduledQuery]] = None,
    ) -> Dict[str, Any]:
        """Apply configuration to serverless workgroup."""
        if self.dry_run:
            return self._dry_run_report(config, scheduled_queries)
        
        result = {}
        
        try:
            # Update workgroup configuration
            result["workgroup"] = self._update_workgroup(config)
            
            # Update namespace IAM roles
            result["namespace"] = self._update_namespace_roles(config)
            
            # Apply scheduled queries if provided
            if scheduled_queries:
                result["scheduled_queries"] = self.query_applier.apply_scheduled_queries(
                    scheduled_queries,
                    config.workgroup_name,
                    config.namespace_name,
                )
            
            return result
        except Exception as e:
            # Provide more detailed error information
            import traceback
            error_details = {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
            }
            raise Exception(f"{type(e).__name__}: {str(e)}") from e

    def _update_workgroup(self, config: ServerlessWorkgroupConfig) -> Dict[str, Any]:
        """Update workgroup settings."""
        update_params = {
            "workgroupName": config.workgroup_name,
            "subnetIds": config.subnet_ids,
            "securityGroupIds": config.security_group_ids,
            "publiclyAccessible": config.publicly_accessible,
        }
        
        if config.config_parameters:
            # config_parameters already in correct format from parameter mapper
            update_params["configParameters"] = config.config_parameters
        
        try:
            response = self.redshift_serverless.update_workgroup(**update_params)
            return {"status": "success", "workgroup": response.get("workgroup", {})}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _update_namespace_roles(self, config: ServerlessWorkgroupConfig) -> Dict[str, Any]:
        """Update namespace IAM roles."""
        if not config.iam_roles:
            return {"status": "skipped", "reason": "No IAM roles to update"}
        
        try:
            response = self.redshift_serverless.update_namespace(
                namespaceName=config.namespace_name,
                iamRoles=config.iam_roles,
                defaultIamRoleArn=config.iam_roles[0] if config.iam_roles else None,
            )
            return {"status": "success", "namespace": response.get("namespace", {})}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _dry_run_report(
        self,
        config: ServerlessWorkgroupConfig,
        scheduled_queries: Optional[List[ScheduledQuery]] = None,
    ) -> Dict[str, Any]:
        """Generate a dry-run report of changes."""
        report = {
            "dry_run": True,
            "workgroup_name": config.workgroup_name,
            "namespace_name": config.namespace_name,
            "changes": {
                "iam_roles": {
                    "action": "update",
                    "roles": config.iam_roles,
                    "default_role": config.iam_roles[0] if config.iam_roles else None,
                },
                "network": {
                    "action": "update",
                    "subnet_ids": config.subnet_ids,
                    "security_group_ids": config.security_group_ids,
                    "publicly_accessible": config.publicly_accessible,
                },
                "config_parameters": {
                    "action": "update" if config.config_parameters else "skip",
                    "parameters": config.config_parameters,
                },
                "tags": {
                    "action": "update" if config.tags else "skip",
                    "tags": config.tags,
                },
            },
        }
        
        # Add scheduled queries to report
        if scheduled_queries:
            report["changes"]["scheduled_queries"] = self.query_applier._dry_run_report(
                scheduled_queries, config.workgroup_name
            )
        
        return report
