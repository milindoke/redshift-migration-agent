"""Extract configuration from Redshift Provisioned clusters."""

import boto3
from typing import Optional, List, Dict, Any
from ..models import (
    ProvisionedClusterConfig,
    IAMRoleConfig,
    VPCConfig,
    SnapshotSchedule,
    LoggingConfig,
    ParameterGroupInfo,
)
from .parameter_groups import ParameterGroupExtractor
from .scheduled_queries import ScheduledQueryExtractor


class ProvisionedClusterExtractor:
    """Extract configuration from a Redshift Provisioned cluster."""

    def __init__(self, region: Optional[str] = None):
        self.redshift = boto3.client("redshift", region_name=region)
        self.events = boto3.client("events", region_name=region)
        self.region = region or boto3.Session().region_name
        self.param_extractor = ParameterGroupExtractor(region=region)
        self.query_extractor = ScheduledQueryExtractor(region=region)

    def extract(self, cluster_identifier: str) -> ProvisionedClusterConfig:
        """Extract complete configuration from a provisioned cluster."""
        cluster = self._get_cluster_details(cluster_identifier)
        
        # Extract parameter group information
        param_group_name = self._extract_parameter_group(cluster)
        param_group_info = None
        if param_group_name:
            param_group_info = self._extract_parameter_group_info(param_group_name)
        
        # Extract scheduled queries
        scheduled_queries = self._extract_scheduled_queries(cluster_identifier)
        
        return ProvisionedClusterConfig(
            cluster_identifier=cluster_identifier,
            iam_roles=self._extract_iam_roles(cluster),
            vpc_config=self._extract_vpc_config(cluster),
            snapshot_schedules=self._extract_snapshot_schedules(cluster_identifier),
            scheduled_queries=scheduled_queries,
            logging_config=self._extract_logging_config(cluster),
            parameter_group_name=param_group_name,
            parameter_group_info=param_group_info,
            maintenance_window=cluster.get("PreferredMaintenanceWindow"),
            maintenance_track=cluster.get("MaintenanceTrackName"),
            snapshot_copy_config=self._extract_snapshot_copy_config(cluster),
            usage_limits=self._extract_usage_limits(cluster_identifier),
            wlm_queues=self._extract_wlm_queues(param_group_name),
            tags=self._extract_tags(cluster_identifier),
            raw_config=cluster,
        )

    def _get_cluster_details(self, cluster_identifier: str) -> Dict[str, Any]:
        """Get cluster details from AWS."""
        response = self.redshift.describe_clusters(ClusterIdentifier=cluster_identifier)
        clusters = response.get("Clusters", [])
        
        if not clusters:
            raise ValueError(f"Cluster {cluster_identifier} not found")
        
        return clusters[0]

    def _extract_iam_roles(self, cluster: Dict[str, Any]) -> List[IAMRoleConfig]:
        """Extract IAM roles attached to the cluster."""
        roles = []
        default_role = cluster.get("DefaultIamRoleArn")
        
        for role in cluster.get("IamRoles", []):
            role_arn = role.get("IamRoleArn")
            if role_arn:
                roles.append(
                    IAMRoleConfig(
                        role_arn=role_arn,
                        is_default=(role_arn == default_role),
                    )
                )
        
        return roles

    def _extract_vpc_config(self, cluster: Dict[str, Any]) -> VPCConfig:
        """Extract VPC and network configuration."""
        vpc_security_groups = cluster.get("VpcSecurityGroups", [])
        security_group_ids = [sg["VpcSecurityGroupId"] for sg in vpc_security_groups]
        
        # Get subnet IDs from cluster subnet group
        subnet_ids = []
        if "ClusterSubnetGroupName" in cluster:
            subnet_group_name = cluster["ClusterSubnetGroupName"]
            subnet_group = self.redshift.describe_cluster_subnet_groups(
                ClusterSubnetGroupName=subnet_group_name
            )
            subnets = subnet_group["ClusterSubnetGroups"][0].get("Subnets", [])
            subnet_ids = [subnet["SubnetIdentifier"] for subnet in subnets]
        
        return VPCConfig(
            vpc_id=cluster.get("VpcId", ""),
            subnet_ids=subnet_ids,
            security_group_ids=security_group_ids,
            publicly_accessible=cluster.get("PubliclyAccessible", False),
        )

    def _extract_snapshot_schedules(
        self, cluster_identifier: str
    ) -> List[SnapshotSchedule]:
        """Extract snapshot schedules associated with the cluster."""
        schedules = []
        
        try:
            response = self.redshift.describe_snapshot_schedules(
                ClusterIdentifier=cluster_identifier
            )
            
            for schedule in response.get("SnapshotSchedules", []):
                schedules.append(
                    SnapshotSchedule(
                        schedule_identifier=schedule["ScheduleIdentifier"],
                        schedule_definitions=schedule.get("ScheduleDefinitions", []),
                        tags={tag["Key"]: tag["Value"] for tag in schedule.get("Tags", [])},
                    )
                )
        except Exception as e:
            print(f"Warning: Could not extract snapshot schedules: {e}")
        
        return schedules

    def _extract_logging_config(self, cluster: Dict[str, Any]) -> Optional[LoggingConfig]:
        """Extract logging configuration."""
        logging_status = cluster.get("LoggingStatus", {})
        
        if not logging_status.get("LoggingEnabled"):
            return None
        
        return LoggingConfig(
            bucket_name=logging_status.get("BucketName"),
            s3_key_prefix=logging_status.get("S3KeyPrefix"),
            log_exports=logging_status.get("LogExports", []),
        )

    def _extract_parameter_group(self, cluster: Dict[str, Any]) -> Optional[str]:
        """Extract parameter group name."""
        param_groups = cluster.get("ClusterParameterGroups", [])
        if param_groups:
            return param_groups[0].get("ParameterGroupName")
        return None

    def _extract_tags(self, cluster_identifier: str) -> Dict[str, str]:
        """Extract tags from the cluster."""
        try:
            response = self.redshift.describe_tags(
                ResourceName=f"arn:aws:redshift:{self.region}:*:cluster:{cluster_identifier}"
            )
            return {tag["Key"]: tag["Value"] for tag in response.get("TaggedResources", [])}
        except Exception:
            return {}

    def _extract_parameter_group_info(
        self, parameter_group_name: str
    ) -> Optional[ParameterGroupInfo]:
        """Extract parameter group information and values."""
        try:
            # Get parameter group metadata
            group_info = self.param_extractor.get_parameter_group_info(parameter_group_name)
            if not group_info:
                return None
            
            # Get parameter values
            parameters = self.param_extractor.extract_parameters(parameter_group_name)
            
            return ParameterGroupInfo(
                name=group_info["name"],
                family=group_info.get("family"),
                description=group_info.get("description"),
                parameters=parameters,
                tags=group_info.get("tags", {}),
            )
        except Exception as e:
            print(f"Warning: Could not extract parameter group info: {e}")
            return None

    def _extract_scheduled_queries(self, cluster_identifier: str) -> List:
        """Extract scheduled queries from EventBridge."""
        try:
            # Try EventBridge Rules first
            queries = self.query_extractor.extract_eventbridge_rules(cluster_identifier)
            
            # Also try EventBridge Scheduler
            scheduler_queries = self.query_extractor.extract_eventbridge_scheduler(
                cluster_identifier
            )
            queries.extend(scheduler_queries)
            
            return queries
        except Exception as e:
            print(f"Warning: Could not extract scheduled queries: {e}")
            return []

    def _extract_snapshot_copy_config(self, cluster: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract cross-region snapshot copy configuration."""
        try:
            snapshot_copy_status = cluster.get("ClusterSnapshotCopyStatus")
            if not snapshot_copy_status:
                return None
            
            config = {
                "destination_region": snapshot_copy_status.get("DestinationRegion"),
                "retention_period": snapshot_copy_status.get("RetentionPeriod"),
                "manual_snapshot_retention_period": snapshot_copy_status.get("ManualSnapshotRetentionPeriod"),
            }
            
            # Extract snapshot copy grant if present
            if snapshot_copy_status.get("SnapshotCopyGrantName"):
                config["snapshot_copy_grant_name"] = snapshot_copy_status.get("SnapshotCopyGrantName")
            
            return config
        except Exception as e:
            print(f"Warning: Could not extract snapshot copy config: {e}")
            return None

    def _extract_usage_limits(self, cluster_identifier: str) -> List:
        """Extract usage limits from the cluster."""
        from ..models import UsageLimit
        
        usage_limits = []
        
        try:
            # Get cluster ARN for usage limit lookup
            response = self.redshift.describe_clusters(ClusterIdentifier=cluster_identifier)
            if not response.get("Clusters"):
                return usage_limits
            
            cluster_arn = response["Clusters"][0].get("ClusterNamespaceArn")
            if not cluster_arn:
                # Construct ARN if not provided
                cluster_arn = f"arn:aws:redshift:{self.region}:*:cluster:{cluster_identifier}"
            
            # List usage limits for this cluster
            paginator = self.redshift.get_paginator("describe_usage_limits")
            for page in paginator.paginate(ClusterIdentifier=cluster_identifier):
                for limit in page.get("UsageLimits", []):
                    usage_limits.append(
                        UsageLimit(
                            limit_id=limit.get("UsageLimitId"),
                            feature_type=limit.get("FeatureType"),
                            limit_type=limit.get("LimitType"),
                            amount=limit.get("Amount"),
                            period=limit.get("Period"),
                            breach_action=limit.get("BreachAction"),
                            tags={tag["Key"]: tag["Value"] for tag in limit.get("Tags", [])},
                        )
                    )
        except Exception as e:
            print(f"Warning: Could not extract usage limits: {e}")
        
        return usage_limits

    def _extract_wlm_queues(self, parameter_group_name: Optional[str]) -> List:
        """Extract WLM queue configuration from parameter group."""
        from ..models import WLMQueue
        import json
        
        wlm_queues = []
        
        if not parameter_group_name:
            return wlm_queues
        
        try:
            # Get WLM configuration from parameter group
            response = self.redshift.describe_cluster_parameters(
                ParameterGroupName=parameter_group_name
            )
            
            # Find wlm_json_configuration parameter
            for param in response.get("Parameters", []):
                if param.get("ParameterName") == "wlm_json_configuration":
                    wlm_config_str = param.get("ParameterValue")
                    if wlm_config_str:
                        wlm_config = json.loads(wlm_config_str)
                        
                        # Extract queue configurations
                        for queue in wlm_config:
                            # Skip the default queue (usually last one with no name)
                            if queue.get("name") or queue.get("query_group"):
                                wlm_queues.append(
                                    WLMQueue(
                                        name=queue.get("name", queue.get("query_group", "unnamed")),
                                        concurrency=queue.get("query_concurrency", 5),
                                        memory_percent=queue.get("memory_percent_to_use"),
                                        user_group=queue.get("user_group", []),
                                        query_group=queue.get("query_group", []),
                                        priority=queue.get("priority"),
                                        timeout=queue.get("max_execution_time"),
                                    )
                                )
                    break
        except Exception as e:
            print(f"Warning: Could not extract WLM configuration: {e}")
        
        return wlm_queues
