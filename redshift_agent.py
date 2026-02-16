#!/usr/bin/env python3
"""
Redshift Migration Strand Agent

A conversational AI agent that helps users migrate from AWS Redshift Provisioned 
clusters to Redshift Serverless using the redshift-migrate CLI tool.
"""

import os
import subprocess
import json
from strands import Agent, tool
from strands.models.bedrock import BedrockModel


@tool
def run_aws_command(service: str, operation: str, parameters: dict = None, region: str = None) -> str:
    """Run any AWS CLI command using boto3-style parameters.
    
    This is a universal tool for executing AWS API operations. Use it when you need
    to interact with AWS services that don't have dedicated tools.
    
    Args:
        service: AWS service name (e.g., 'redshift', 'redshift-serverless', 'ec2', 's3')
        operation: Operation name in snake_case (e.g., 'describe_clusters', 'list_namespaces')
        parameters: Dictionary of parameters for the operation (optional)
        region: AWS region (optional, uses default if not specified)
    
    Returns:
        JSON output from the AWS API call
    
    Examples:
        - List Redshift Serverless namespaces:
          service='redshift-serverless', operation='list_namespaces'
        - List Redshift Serverless workgroups:
          service='redshift-serverless', operation='list_workgroups'
        - Describe a specific namespace:
          service='redshift-serverless', operation='get_namespace', 
          parameters={'namespaceName': 'my-namespace'}
    """
    import boto3
    from botocore.exceptions import ClientError
    
    try:
        # Create boto3 client
        client_args = {}
        if region:
            client_args['region_name'] = region
        
        client = boto3.client(service, **client_args)
        
        # Call the operation
        if parameters:
            response = getattr(client, operation)(**parameters)
        else:
            response = getattr(client, operation)()
        
        # Remove ResponseMetadata for cleaner output
        if 'ResponseMetadata' in response:
            del response['ResponseMetadata']
        
        # Format the output nicely
        return json.dumps(response, indent=2, default=str)
        
    except ClientError as e:
        return f"AWS API Error: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
    except AttributeError as e:
        return f"Invalid operation '{operation}' for service '{service}'. Error: {str(e)}"
    except Exception as e:
        return f"Error executing AWS command: {str(e)}"


@tool
def get_cluster_usage_limits(cluster_id: str, region: str = None) -> str:
    """Get usage limits from a Redshift provisioned cluster.
    
    Usage limits control resource consumption for features like:
    - Spectrum: Limit data scanned by Redshift Spectrum queries
    - Concurrency Scaling: Limit time using concurrency scaling clusters
    - Cross-Region Datasharing: Limit data transferred for datasharing
    
    Args:
        cluster_id: The provisioned cluster ID
        region: AWS region (optional, uses default if not specified)
    
    Returns:
        JSON with all usage limits configured for the cluster
    """
    import boto3
    from botocore.exceptions import ClientError
    
    try:
        redshift = boto3.client("redshift", region_name=region)
        
        usage_limits = []
        
        # List usage limits for this cluster
        paginator = redshift.get_paginator("describe_usage_limits")
        for page in paginator.paginate(ClusterIdentifier=cluster_id):
            for limit in page.get("UsageLimits", []):
                usage_limits.append({
                    "limit_id": limit.get("UsageLimitId"),
                    "feature_type": limit.get("FeatureType"),
                    "limit_type": limit.get("LimitType"),
                    "amount": limit.get("Amount"),
                    "period": limit.get("Period"),
                    "breach_action": limit.get("BreachAction"),
                    "tags": {tag["Key"]: tag["Value"] for tag in limit.get("Tags", [])}
                })
        
        if not usage_limits:
            return json.dumps({
                "cluster_id": cluster_id,
                "usage_limits_count": 0,
                "message": "No usage limits configured for this cluster"
            }, indent=2)
        
        return json.dumps({
            "cluster_id": cluster_id,
            "usage_limits_count": len(usage_limits),
            "usage_limits": usage_limits
        }, indent=2)
        
    except ClientError as e:
        return f"AWS API Error: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
    except Exception as e:
        return f"Error getting usage limits: {str(e)}"


@tool
def create_serverless_usage_limit(
    workgroup_name: str,
    usage_type: str,
    amount: int,
    period: str = "monthly",
    breach_action: str = "log",
    region: str = None
) -> str:
    """Create a usage limit for a Redshift Serverless workgroup.
    
    Serverless usage limits control RPU (Redshift Processing Unit) consumption.
    
    Args:
        workgroup_name: The serverless workgroup name
        usage_type: Type of usage limit - must be "serverless-compute" for serverless
        amount: Limit amount in RPU-hours (e.g., 60 for 60 RPU-hours)
        period: Time period - "daily", "weekly", or "monthly" (default: monthly)
        breach_action: Action when limit is breached - "log", "emit-metric", or "deactivate" (default: log)
        region: AWS region (optional, uses default if not specified)
    
    Returns:
        Created usage limit details
    """
    import boto3
    from botocore.exceptions import ClientError
    
    try:
        redshift_serverless = boto3.client("redshift-serverless", region_name=region)
        
        # Create usage limit for serverless workgroup
        response = redshift_serverless.create_usage_limit(
            resourceArn=f"arn:aws:redshift-serverless:{region or 'us-east-1'}:*:workgroup/*",
            usageType=usage_type,
            amount=amount,
            period=period,
            breachAction=breach_action
        )
        
        result = {
            "status": "success",
            "workgroup_name": workgroup_name,
            "usage_limit_id": response.get("usageLimit", {}).get("usageLimitId"),
            "usage_type": usage_type,
            "amount": amount,
            "period": period,
            "breach_action": breach_action,
            "message": f"Usage limit created for workgroup '{workgroup_name}'"
        }
        
        return json.dumps(result, indent=2)
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        
        if error_code == "ConflictException":
            return json.dumps({
                "status": "already_exists",
                "message": f"Usage limit already exists for workgroup '{workgroup_name}'"
            }, indent=2)
        
        return f"AWS API Error: {error_code} - {error_msg}"
    except Exception as e:
        return f"Error creating usage limit: {str(e)}"


@tool
def migrate_usage_limits_to_serverless(
    cluster_id: str,
    workgroup_name: str,
    region: str = None,
    dry_run: bool = False
) -> str:
    """Migrate usage limits from provisioned cluster to serverless workgroup.
    
    Note: Provisioned and Serverless use different usage limit types:
    - Provisioned: spectrum, concurrency-scaling, cross-region-datasharing
    - Serverless: serverless-compute (RPU-hours)
    
    This tool provides recommendations for equivalent serverless limits based on
    provisioned cluster usage patterns.
    
    Args:
        cluster_id: Source provisioned cluster ID
        workgroup_name: Target serverless workgroup name
        region: AWS region (optional, uses default if not specified)
        dry_run: Preview recommendations without creating limits (default: False)
    
    Returns:
        Migration results with recommendations
    """
    import boto3
    from botocore.exceptions import ClientError
    
    try:
        redshift = boto3.client("redshift", region_name=region)
        
        results = {
            "cluster_id": cluster_id,
            "workgroup_name": workgroup_name,
            "dry_run": dry_run,
            "provisioned_limits": [],
            "serverless_recommendations": [],
            "notes": []
        }
        
        # Get usage limits from provisioned cluster
        paginator = redshift.get_paginator("describe_usage_limits")
        for page in paginator.paginate(ClusterIdentifier=cluster_id):
            for limit in page.get("UsageLimits", []):
                results["provisioned_limits"].append({
                    "feature_type": limit.get("FeatureType"),
                    "limit_type": limit.get("LimitType"),
                    "amount": limit.get("Amount"),
                    "period": limit.get("Period"),
                    "breach_action": limit.get("BreachAction")
                })
        
        if not results["provisioned_limits"]:
            results["notes"].append("No usage limits found on provisioned cluster")
            results["notes"].append("Consider setting RPU-hour limits for serverless workgroup")
            results["serverless_recommendations"].append({
                "usage_type": "serverless-compute",
                "amount": 60,
                "period": "daily",
                "breach_action": "log",
                "reason": "Default recommendation: 60 RPU-hours per day"
            })
        else:
            # Provide recommendations based on provisioned limits
            results["notes"].append("Provisioned usage limits don't directly map to serverless")
            results["notes"].append("Serverless uses RPU-hours for compute limits")
            
            # Check for concurrency scaling limits (most relevant to serverless)
            has_concurrency_limit = any(
                l["feature_type"] == "concurrency-scaling" 
                for l in results["provisioned_limits"]
            )
            
            if has_concurrency_limit:
                results["serverless_recommendations"].append({
                    "usage_type": "serverless-compute",
                    "amount": 120,
                    "period": "daily",
                    "breach_action": "log",
                    "reason": "Cluster has concurrency scaling limits - recommended 120 RPU-hours/day"
                })
            else:
                results["serverless_recommendations"].append({
                    "usage_type": "serverless-compute",
                    "amount": 60,
                    "period": "daily",
                    "breach_action": "log",
                    "reason": "Standard recommendation: 60 RPU-hours per day"
                })
        
        results["total_provisioned_limits"] = len(results["provisioned_limits"])
        results["total_recommendations"] = len(results["serverless_recommendations"])
        
        return json.dumps(results, indent=2)
        
    except ClientError as e:
        return f"AWS API Error: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
    except Exception as e:
        return f"Error migrating usage limits: {str(e)}"


@tool
def get_cluster_maintenance_settings(cluster_id: str, region: str = None) -> str:
    """Get maintenance track and window settings from a Redshift provisioned cluster.
    
    Args:
        cluster_id: The provisioned cluster ID
        region: AWS region (optional, uses default if not specified)
    
    Returns:
        JSON with maintenance track, maintenance window, and next maintenance window
    """
    import boto3
    from botocore.exceptions import ClientError
    
    try:
        redshift = boto3.client("redshift", region_name=region)
        
        response = redshift.describe_clusters(ClusterIdentifier=cluster_id)
        clusters = response.get("Clusters", [])
        
        if not clusters:
            return f"Cluster '{cluster_id}' not found"
        
        cluster = clusters[0]
        
        settings = {
            "cluster_id": cluster_id,
            "maintenance_track": cluster.get("MaintenanceTrackName", "current"),
            "maintenance_window": cluster.get("PreferredMaintenanceWindow"),
            "next_maintenance_window": cluster.get("NextMaintenanceWindowStartTime"),
            "allow_version_upgrade": cluster.get("AllowVersionUpgrade", True),
            "cluster_version": cluster.get("ClusterVersion"),
        }
        
        return json.dumps(settings, indent=2, default=str)
        
    except ClientError as e:
        return f"AWS API Error: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
    except Exception as e:
        return f"Error getting maintenance settings: {str(e)}"


@tool
def get_cluster_snapshot_copy_settings(cluster_id: str, region: str = None) -> str:
    """Get cross-region snapshot copy settings from a Redshift provisioned cluster.
    
    Args:
        cluster_id: The provisioned cluster ID
        region: AWS region (optional, uses default if not specified)
    
    Returns:
        JSON with snapshot copy configuration including destination region and retention
    """
    import boto3
    from botocore.exceptions import ClientError
    
    try:
        redshift = boto3.client("redshift", region_name=region)
        
        response = redshift.describe_clusters(ClusterIdentifier=cluster_id)
        clusters = response.get("Clusters", [])
        
        if not clusters:
            return f"Cluster '{cluster_id}' not found"
        
        cluster = clusters[0]
        snapshot_copy_status = cluster.get("ClusterSnapshotCopyStatus")
        
        if not snapshot_copy_status:
            return json.dumps({
                "cluster_id": cluster_id,
                "snapshot_copy_enabled": False,
                "message": "Cross-region snapshot copy is not enabled for this cluster"
            }, indent=2)
        
        settings = {
            "cluster_id": cluster_id,
            "snapshot_copy_enabled": True,
            "destination_region": snapshot_copy_status.get("DestinationRegion"),
            "retention_period_days": snapshot_copy_status.get("RetentionPeriod"),
            "manual_snapshot_retention_period_days": snapshot_copy_status.get("ManualSnapshotRetentionPeriod", -1),
            "snapshot_copy_grant_name": snapshot_copy_status.get("SnapshotCopyGrantName"),
        }
        
        return json.dumps(settings, indent=2, default=str)
        
    except ClientError as e:
        return f"AWS API Error: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
    except Exception as e:
        return f"Error getting snapshot copy settings: {str(e)}"


@tool
def configure_serverless_snapshot_copy(
    namespace_name: str,
    destination_region: str,
    retention_period: int = 7,
    snapshot_copy_grant_name: str = None,
    region: str = None
) -> str:
    """Configure cross-region snapshot copy for a Redshift Serverless namespace.
    
    Args:
        namespace_name: The serverless namespace name
        destination_region: AWS region to copy snapshots to
        retention_period: Number of days to retain snapshots (default: 7)
        snapshot_copy_grant_name: KMS grant name for encrypted snapshots (optional)
        region: Source AWS region (optional, uses default if not specified)
    
    Returns:
        Configuration result
    """
    import boto3
    from botocore.exceptions import ClientError
    
    try:
        redshift_serverless = boto3.client("redshift-serverless", region_name=region)
        
        # Configure snapshot copy for the namespace
        params = {
            "namespaceName": namespace_name,
            "destinationRegion": destination_region,
            "retentionPeriod": retention_period,
        }
        
        if snapshot_copy_grant_name:
            params["snapshotCopyGrantName"] = snapshot_copy_grant_name
        
        response = redshift_serverless.create_snapshot_copy_configuration(**params)
        
        result = {
            "status": "success",
            "namespace_name": namespace_name,
            "destination_region": destination_region,
            "retention_period_days": retention_period,
            "snapshot_copy_grant": snapshot_copy_grant_name,
            "message": f"Cross-region snapshot copy configured for namespace '{namespace_name}'"
        }
        
        return json.dumps(result, indent=2)
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        
        if error_code == "ConflictException":
            return json.dumps({
                "status": "already_exists",
                "message": f"Snapshot copy configuration already exists for namespace '{namespace_name}'"
            }, indent=2)
        
        return f"AWS API Error: {error_code} - {error_msg}"
    except Exception as e:
        return f"Error configuring snapshot copy: {str(e)}"


@tool
def list_redshift_clusters(region: str = None) -> str:
    """List all Redshift provisioned clusters in the account.
    
    Args:
        region: AWS region (optional, uses default if not specified)
    
    Returns:
        List of Redshift clusters with their IDs, status, and basic information
    """
    cmd = ["aws", "redshift", "describe-clusters"]
    if region:
        cmd.extend(["--region", region])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        clusters_data = json.loads(result.stdout)
        
        if not clusters_data.get("Clusters"):
            return "No Redshift provisioned clusters found in this region."
        
        # Format the output nicely
        output = []
        for cluster in clusters_data["Clusters"]:
            output.append(f"Cluster ID: {cluster['ClusterIdentifier']}")
            output.append(f"  Status: {cluster['ClusterStatus']}")
            output.append(f"  Node Type: {cluster['NodeType']}")
            output.append(f"  Number of Nodes: {cluster['NumberOfNodes']}")
            output.append(f"  Region: {cluster.get('AvailabilityZone', 'N/A')}")
            output.append(f"  Endpoint: {cluster.get('Endpoint', {}).get('Address', 'N/A')}")
            output.append("")
        
        return "\n".join(output)
    except subprocess.CalledProcessError as e:
        return f"Error listing clusters: {e.stderr}"
    except json.JSONDecodeError as e:
        return f"Error parsing cluster data: {str(e)}"


@tool
def extract_cluster_config(cluster_id: str, region: str = None) -> str:
    """Extract configuration from a Redshift provisioned cluster.
    
    Args:
        cluster_id: The ID of the provisioned cluster to extract from
        region: AWS region (optional, uses default if not specified)
    
    Returns:
        JSON string with extracted configuration including IAM roles, VPC, 
        parameter groups, scheduled queries, and other settings
    """
    cmd = ["redshift-migrate", "extract", "--cluster-id", cluster_id]
    if region:
        cmd.extend(["--region", region])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error extracting configuration: {e.stderr}"


@tool
def migrate_cluster(
    cluster_id: str,
    workgroup_name: str = None,
    namespace_name: str = None,
    create_if_missing: bool = True,
    create_snapshot: bool = False,
    snapshot_name: str = None,
    max_capacity: int = 512,
    region: str = None,
    dry_run: bool = False
) -> str:
    """Perform a full migration from provisioned cluster to serverless.
    
    Args:
        cluster_id: Source provisioned cluster ID
        workgroup_name: Target workgroup name (defaults to cluster_id)
        namespace_name: Target namespace name (defaults to cluster_id)
        create_if_missing: Create workgroup/namespace if they don't exist
        create_snapshot: Create new snapshot from cluster before restoring
        snapshot_name: Use existing snapshot for restore (mutually exclusive with create_snapshot)
        max_capacity: Maximum RPU capacity for workgroup (default: 512)
        region: AWS region (optional)
        dry_run: Preview changes without applying
    
    Returns:
        Migration results including status of each component
    """
    cmd = ["redshift-migrate", "migrate", "--cluster-id", cluster_id]
    
    if workgroup_name:
        cmd.extend(["--workgroup", workgroup_name])
    if namespace_name:
        cmd.extend(["--namespace", namespace_name])
    if create_if_missing:
        cmd.append("--create-if-missing")
    if create_snapshot:
        cmd.append("--create-snapshot")
    if snapshot_name:
        cmd.extend(["--snapshot-name", snapshot_name])
    if max_capacity:
        cmd.extend(["--max-capacity", str(max_capacity)])
    if region:
        cmd.extend(["--region", region])
    if dry_run:
        cmd.append("--dry-run")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Migration error: {e.stderr}\n\nOutput: {e.stdout}"


@tool
def apply_configuration(
    config_file: str,
    workgroup_name: str,
    namespace_name: str = None,
    create_if_missing: bool = False,
    create_snapshot: bool = False,
    snapshot_name: str = None,
    max_capacity: int = 512,
    region: str = None,
    dry_run: bool = False
) -> str:
    """Apply extracted configuration to a serverless workgroup.
    
    Args:
        config_file: Path to extracted configuration JSON file
        workgroup_name: Target workgroup name
        namespace_name: Target namespace name (defaults to workgroup_name)
        create_if_missing: Create workgroup/namespace if they don't exist
        create_snapshot: Create new snapshot from source cluster
        snapshot_name: Use existing snapshot for restore
        max_capacity: Maximum RPU capacity (default: 512)
        region: AWS region (optional)
        dry_run: Preview changes without applying
    
    Returns:
        Application results for each component
    """
    cmd = ["redshift-migrate", "apply", "--config", config_file, "--workgroup", workgroup_name]
    
    if namespace_name:
        cmd.extend(["--namespace", namespace_name])
    if create_if_missing:
        cmd.append("--create-if-missing")
    if create_snapshot:
        cmd.append("--create-snapshot")
    if snapshot_name:
        cmd.extend(["--snapshot-name", snapshot_name])
    if max_capacity:
        cmd.extend(["--max-capacity", str(max_capacity)])
    if region:
        cmd.extend(["--region", region])
    if dry_run:
        cmd.append("--dry-run")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Apply error: {e.stderr}\n\nOutput: {e.stdout}"


@tool
def list_scheduled_queries(cluster_id: str, region: str = None) -> str:
    """List all scheduled queries associated with a Redshift provisioned cluster.
    
    This extracts scheduled queries from both EventBridge Rules and EventBridge Scheduler
    that target the specified cluster.
    
    Args:
        cluster_id: The provisioned cluster ID to check for scheduled queries
        region: AWS region (optional, uses default if not specified)
    
    Returns:
        JSON list of scheduled queries with their schedules, SQL, and status
    """
    import boto3
    from botocore.exceptions import ClientError
    
    try:
        # Use boto3 to extract scheduled queries
        events = boto3.client("events", region_name=region)
        scheduler = boto3.client("scheduler", region_name=region)
        
        scheduled_queries = []
        
        # Extract from EventBridge Rules
        try:
            paginator = events.get_paginator("list_rules")
            for page in paginator.paginate():
                for rule in page.get("Rules", []):
                    rule_name = rule.get("Name")
                    
                    # Get targets for this rule
                    targets_response = events.list_targets_by_rule(Rule=rule_name)
                    
                    for target in targets_response.get("Targets", []):
                        if "redshift-data" in target.get("Arn", ""):
                            input_str = target.get("Input", "{}")
                            input_data = json.loads(input_str)
                            
                            if input_data.get("ClusterIdentifier") == cluster_id:
                                scheduled_queries.append({
                                    "name": rule_name,
                                    "type": "EventBridge Rule",
                                    "schedule": rule.get("ScheduleExpression", ""),
                                    "query": input_data.get("Sql", "")[:100] + "...",
                                    "database": input_data.get("Database", ""),
                                    "enabled": rule.get("State") == "ENABLED"
                                })
        except Exception as e:
            print(f"Warning: Could not extract EventBridge rules: {e}")
        
        # Extract from EventBridge Scheduler
        try:
            groups_response = scheduler.list_schedule_groups()
            
            for group in groups_response.get("ScheduleGroups", []):
                group_name = group.get("Name")
                schedules_response = scheduler.list_schedules(GroupName=group_name)
                
                for schedule in schedules_response.get("Schedules", []):
                    schedule_name = schedule.get("Name")
                    schedule_detail = scheduler.get_schedule(
                        Name=schedule_name,
                        GroupName=group_name
                    )
                    
                    target = schedule_detail.get("Target", {})
                    if "redshift-data" in target.get("Arn", ""):
                        input_data = json.loads(target.get("Input", "{}"))
                        
                        if input_data.get("ClusterIdentifier") == cluster_id:
                            scheduled_queries.append({
                                "name": schedule_name,
                                "type": "EventBridge Scheduler",
                                "schedule": schedule_detail.get("ScheduleExpression", ""),
                                "query": input_data.get("Sql", "")[:100] + "...",
                                "database": input_data.get("Database", ""),
                                "enabled": schedule_detail.get("State") == "ENABLED"
                            })
        except Exception as e:
            print(f"Warning: Could not extract EventBridge Scheduler schedules: {e}")
        
        if not scheduled_queries:
            return f"No scheduled queries found for cluster '{cluster_id}'"
        
        return json.dumps({
            "cluster_id": cluster_id,
            "total_queries": len(scheduled_queries),
            "scheduled_queries": scheduled_queries
        }, indent=2)
        
    except ClientError as e:
        return f"AWS API Error: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
    except Exception as e:
        return f"Error listing scheduled queries: {str(e)}"


@tool
def migrate_scheduled_queries(
    cluster_id: str,
    workgroup_name: str,
    namespace_name: str = None,
    region: str = None,
    dry_run: bool = False
) -> str:
    """Migrate scheduled queries from a provisioned cluster to a serverless workgroup.
    
    This extracts scheduled queries from the provisioned cluster and recreates them
    to target the serverless workgroup using EventBridge Scheduler.
    
    Args:
        cluster_id: Source provisioned cluster ID
        workgroup_name: Target serverless workgroup name
        namespace_name: Target namespace name (defaults to workgroup_name)
        region: AWS region (optional, uses default if not specified)
        dry_run: Preview changes without applying (default: False)
    
    Returns:
        Migration results showing which queries were migrated
    """
    import boto3
    from botocore.exceptions import ClientError
    
    try:
        events = boto3.client("events", region_name=region)
        scheduler = boto3.client("scheduler", region_name=region)
        iam = boto3.client("iam", region_name=region)
        
        if not namespace_name:
            namespace_name = workgroup_name
        
        results = {
            "cluster_id": cluster_id,
            "workgroup_name": workgroup_name,
            "namespace_name": namespace_name,
            "dry_run": dry_run,
            "migrated_queries": []
        }
        
        # Get or create execution role for EventBridge
        role_name = "RedshiftScheduledQueryExecutionRole"
        try:
            role_response = iam.get_role(RoleName=role_name)
            execution_role_arn = role_response["Role"]["Arn"]
        except iam.exceptions.NoSuchEntityException:
            if dry_run:
                execution_role_arn = f"arn:aws:iam::ACCOUNT_ID:role/{role_name}"
            else:
                # Create the role
                trust_policy = {
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {"Service": "scheduler.amazonaws.com"},
                        "Action": "sts:AssumeRole"
                    }]
                }
                
                role_response = iam.create_role(
                    RoleName=role_name,
                    AssumeRolePolicyDocument=json.dumps(trust_policy),
                    Description="Allows EventBridge Scheduler to execute Redshift queries"
                )
                execution_role_arn = role_response["Role"]["Arn"]
                
                # Attach policy for Redshift Data API
                policy_document = {
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": [
                            "redshift-data:ExecuteStatement",
                            "redshift-data:DescribeStatement",
                            "redshift-data:GetStatementResult"
                        ],
                        "Resource": "*"
                    }]
                }
                
                iam.put_role_policy(
                    RoleName=role_name,
                    PolicyName="RedshiftDataAPIAccess",
                    PolicyDocument=json.dumps(policy_document)
                )
        
        # Extract scheduled queries from provisioned cluster
        scheduled_queries = []
        
        # From EventBridge Rules
        paginator = events.get_paginator("list_rules")
        for page in paginator.paginate():
            for rule in page.get("Rules", []):
                rule_name = rule.get("Name")
                targets_response = events.list_targets_by_rule(Rule=rule_name)
                
                for target in targets_response.get("Targets", []):
                    if "redshift-data" in target.get("Arn", ""):
                        input_str = target.get("Input", "{}")
                        input_data = json.loads(input_str)
                        
                        if input_data.get("ClusterIdentifier") == cluster_id:
                            scheduled_queries.append({
                                "name": rule_name,
                                "schedule": rule.get("ScheduleExpression", ""),
                                "query": input_data.get("Sql", ""),
                                "database": input_data.get("Database", ""),
                                "enabled": rule.get("State") == "ENABLED"
                            })
        
        # Migrate each query
        for query in scheduled_queries:
            schedule_name = f"{workgroup_name}-{query['name']}"
            
            target_input = {
                "WorkgroupName": workgroup_name,
                "Database": query["database"],
                "Sql": query["query"]
            }
            
            if dry_run:
                results["migrated_queries"].append({
                    "original_name": query["name"],
                    "new_name": schedule_name,
                    "schedule": query["schedule"],
                    "database": query["database"],
                    "status": "DRY_RUN - would be created"
                })
            else:
                try:
                    response = scheduler.create_schedule(
                        Name=schedule_name,
                        ScheduleExpression=query["schedule"],
                        Target={
                            "Arn": f"arn:aws:scheduler:::aws-sdk:redshiftdata:executeStatement",
                            "RoleArn": execution_role_arn,
                            "Input": json.dumps(target_input)
                        },
                        FlexibleTimeWindow={"Mode": "OFF"},
                        State="ENABLED" if query["enabled"] else "DISABLED"
                    )
                    
                    results["migrated_queries"].append({
                        "original_name": query["name"],
                        "new_name": schedule_name,
                        "schedule": query["schedule"],
                        "database": query["database"],
                        "status": "created",
                        "schedule_arn": response.get("ScheduleArn")
                    })
                except scheduler.exceptions.ConflictException:
                    results["migrated_queries"].append({
                        "original_name": query["name"],
                        "new_name": schedule_name,
                        "status": "already_exists"
                    })
                except Exception as e:
                    results["migrated_queries"].append({
                        "original_name": query["name"],
                        "new_name": schedule_name,
                        "status": "error",
                        "error": str(e)
                    })
        
        results["total_migrated"] = len([q for q in results["migrated_queries"] if q["status"] in ["created", "already_exists"]])
        
        return json.dumps(results, indent=2)
        
    except ClientError as e:
        return f"AWS API Error: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
    except Exception as e:
        return f"Error migrating scheduled queries: {str(e)}"


@tool
def get_migration_help(topic: str = None) -> str:
    """Get help information about the migration tool.
    
    Args:
        topic: Specific topic to get help on (extract, apply, migrate, scheduled_queries, or general)
    
    Returns:
        Help text for the specified topic
    """
    if topic == "usage_limits":
        return """
Usage Limits Migration:
Migrate usage limits from provisioned cluster to serverless workgroup.

Available Tools:
1. get_cluster_usage_limits - Get usage limits from provisioned cluster
2. create_serverless_usage_limit - Create usage limit for serverless workgroup
3. migrate_usage_limits_to_serverless - Get recommendations and migrate

Key Differences:
- Provisioned: spectrum, concurrency-scaling, cross-region-datasharing
- Serverless: serverless-compute (RPU-hours)

Usage Limit Types:
Provisioned:
- spectrum: Limit data scanned by Spectrum queries (in TB)
- concurrency-scaling: Limit time using concurrency scaling (in minutes)
- cross-region-datasharing: Limit data transferred for datasharing (in TB)

Serverless:
- serverless-compute: Limit RPU-hours consumed by workgroup

Periods: daily, weekly, monthly
Breach Actions: log, emit-metric, deactivate (serverless) / disable (provisioned)

Example workflow:
1. Check limits: get_cluster_usage_limits(cluster_id="my-cluster")
2. Get recommendations: migrate_usage_limits_to_serverless(
                          cluster_id="my-cluster",
                          workgroup_name="my-wg",
                          dry_run=True)
3. Create limit: create_serverless_usage_limit(
                   workgroup_name="my-wg",
                   usage_type="serverless-compute",
                   amount=60,
                   period="daily",
                   breach_action="log")

Note: Limits don't directly map - recommendations provided based on usage patterns.
"""
    elif topic == "maintenance_snapshot":
        return """
Maintenance Track and Snapshot Copy Migration:
Migrate maintenance and snapshot settings from provisioned to serverless.

Available Tools:
1. get_cluster_maintenance_settings - Get maintenance track and window
2. get_cluster_snapshot_copy_settings - Get cross-region snapshot copy config
3. configure_serverless_snapshot_copy - Set up snapshot copy for serverless

Key Differences:
- Provisioned: Manual maintenance windows (e.g., "sun:05:00-sun:05:30")
- Serverless: Automatic maintenance windows (AWS managed)
- Provisioned: Maintenance tracks (current, trailing, preview)
- Serverless: Always on latest version automatically

Snapshot Copy:
- Both support cross-region snapshot copy
- Retention periods can be migrated
- KMS encryption grants are preserved
- Configure after namespace creation

Example workflow:
1. Check settings: get_cluster_maintenance_settings(cluster_id="my-cluster")
2. Check snapshot copy: get_cluster_snapshot_copy_settings(cluster_id="my-cluster")
3. Migrate cluster to serverless
4. Configure snapshot copy: configure_serverless_snapshot_copy(
                              namespace_name="my-namespace",
                              destination_region="us-west-2",
                              retention_period=7)

Note: Serverless handles maintenance automatically, no manual window needed.
"""
    elif topic == "scheduled_queries":
        return """
Scheduled Query Migration:
Migrate scheduled queries from provisioned cluster to serverless workgroup.

Available Tools:
1. list_scheduled_queries - List all scheduled queries for a cluster
2. migrate_scheduled_queries - Migrate queries to serverless workgroup

How it works:
- Extracts queries from EventBridge Rules and EventBridge Scheduler
- Recreates them to target the serverless workgroup
- Uses Redshift Data API for serverless execution
- Preserves schedule expressions and query SQL
- Maintains enabled/disabled state

Example workflow:
1. List queries: list_scheduled_queries(cluster_id="my-cluster")
2. Preview migration: migrate_scheduled_queries(cluster_id="my-cluster", 
                                                 workgroup_name="my-wg", 
                                                 dry_run=True)
3. Migrate: migrate_scheduled_queries(cluster_id="my-cluster", 
                                       workgroup_name="my-wg")

Note: Requires EventBridge and Redshift Data API permissions.
"""
    elif topic == "extract":
        return """
Extract Command:
Extracts configuration from a provisioned cluster without making any changes.

Usage: redshift-migrate extract --cluster-id <id> [--output <file>] [--region <region>]

Extracts:
- IAM roles and default role
- VPC configuration (subnets, security groups)
- Parameter groups (10+ mappable parameters)
- Scheduled queries (EventBridge Rules/Scheduler)
- Snapshot schedules
- Maintenance track and window
- Cross-region snapshot copy settings
- Usage limits (spectrum, concurrency-scaling, datasharing)
- Tags and logging configuration
"""
    elif topic == "apply":
        return """
Apply Command:
Applies extracted configuration to a serverless workgroup.

Usage: redshift-migrate apply --config <file> --workgroup <name> [options]

Options:
- --namespace: Namespace name (defaults to workgroup name)
- --create-if-missing: Create workgroup/namespace if needed
- --create-snapshot: Create new snapshot from source cluster
- --snapshot-name: Use existing snapshot
- --max-capacity: Maximum RPU (default: 512)
- --dry-run: Preview without applying
"""
    elif topic == "migrate":
        return """
Migrate Command:
Full migration in one command (extract + apply).

Usage: redshift-migrate migrate --cluster-id <id> [options]

Simplest usage (uses smart defaults):
redshift-migrate migrate --cluster-id my-cluster --create-if-missing --create-snapshot --region us-east-1

Options:
- --workgroup: Target workgroup (defaults to cluster-id)
- --namespace: Target namespace (defaults to cluster-id)
- --create-if-missing: Create resources if needed
- --create-snapshot: Create and restore from new snapshot
- --snapshot-name: Use existing snapshot
- --max-capacity: Maximum RPU (default: 512)
- --dry-run: Preview without applying
"""
    else:
        return """
Redshift Migration Tool Help

Commands:
1. extract - Extract configuration from provisioned cluster
2. apply - Apply configuration to serverless workgroup
3. migrate - Full migration (extract + apply)
4. list_scheduled_queries - List scheduled queries for a cluster
5. migrate_scheduled_queries - Migrate scheduled queries to serverless
6. get_cluster_maintenance_settings - Get maintenance track and window
7. get_cluster_snapshot_copy_settings - Get cross-region snapshot copy config
8. configure_serverless_snapshot_copy - Configure snapshot copy for serverless
9. get_cluster_usage_limits - Get usage limits from provisioned cluster
10. create_serverless_usage_limit - Create usage limit for serverless workgroup
11. migrate_usage_limits_to_serverless - Migrate usage limits with recommendations

Key Concepts:
- Namespace: Contains database, users, and data
- Workgroup: Compute resources that query the namespace
- Snapshots: Preserve all data from provisioned cluster
- Parameter Mapping: Automatically maps 10+ parameters
- Scheduled Queries: Migrates EventBridge rules to target serverless workgroup
- Maintenance: Serverless uses automatic maintenance (no manual windows)
- Snapshot Copy: Can be configured for cross-region backup
- Usage Limits: Control resource consumption (different types for provisioned vs serverless)

Use get_migration_help with topic='extract', 'apply', 'migrate', 'scheduled_queries', 'maintenance_snapshot', or 'usage_limits' for detailed help.
"""


# System prompt for the agent
SYSTEM_PROMPT = """You are a Redshift Migration Assistant that helps users migrate from AWS Redshift Provisioned clusters to Redshift Serverless.

Your role is to:
1. Understand user needs through conversation
2. Recommend the best migration approach
3. Guide users through the migration process
4. Help troubleshoot issues
5. Use AWS APIs directly when needed for cluster inspection or validation

Available Tools:
- run_aws_command: Universal tool to run ANY AWS API operation (use for namespaces, workgroups, snapshots, etc.)
- list_redshift_clusters: List all Redshift provisioned clusters in the account
- extract_cluster_config: Extract configuration from a specific provisioned cluster
- migrate_cluster: Full migration (extract + apply)
- apply_configuration: Apply extracted config to serverless
- list_scheduled_queries: List scheduled queries for a provisioned cluster
- migrate_scheduled_queries: Migrate scheduled queries to serverless workgroup
- get_cluster_maintenance_settings: Get maintenance track and window from provisioned cluster
- get_cluster_snapshot_copy_settings: Get cross-region snapshot copy settings
- configure_serverless_snapshot_copy: Configure cross-region snapshot copy for serverless namespace
- get_cluster_usage_limits: Get usage limits from provisioned cluster
- create_serverless_usage_limit: Create usage limit for serverless workgroup
- migrate_usage_limits_to_serverless: Migrate usage limits with recommendations
- get_migration_help: Context-aware help system

When users ask about AWS resources (namespaces, workgroups, snapshots, etc.):
- Use run_aws_command with the appropriate service and operation
- For Redshift Serverless: service='redshift-serverless'
  - List namespaces: operation='list_namespaces'
  - List workgroups: operation='list_workgroups'
  - Get namespace details: operation='get_namespace', parameters={'namespaceName': 'name'}
- For Redshift Provisioned: service='redshift'
  - List snapshots: operation='describe_cluster_snapshots'
  - Describe cluster: operation='describe_clusters', parameters={'ClusterIdentifier': 'id'}

Key Migration Patterns:

1. SIMPLEST (Recommended for most users):
   - One command with smart defaults
   - Creates snapshot automatically
   - Workgroup/namespace names match cluster ID
   
2. STEP-BY-STEP (For cautious users):
   - Extract configuration first
   - Review extracted config
   - Apply with dry-run to preview
   - Apply for real

3. CONFIGURATION ONLY (No data migration):
   - Migrate settings without snapshot
   - Creates empty namespace with credentials

4. SCHEDULED QUERIES:
   - List scheduled queries: list_scheduled_queries(cluster_id, region)
   - Migrate queries: migrate_scheduled_queries(cluster_id, workgroup_name, namespace_name, region, dry_run)
   - Queries are recreated to target the serverless workgroup
   - Uses EventBridge Scheduler and Redshift Data API

5. MAINTENANCE AND SNAPSHOT SETTINGS:
   - Get maintenance track: get_cluster_maintenance_settings(cluster_id, region)
   - Get snapshot copy settings: get_cluster_snapshot_copy_settings(cluster_id, region)
   - Configure serverless snapshot copy: configure_serverless_snapshot_copy(namespace_name, destination_region, retention_period, region)
   - Note: Serverless uses automatic maintenance windows, but you can configure snapshot copy

6. USAGE LIMITS:
   - Get usage limits: get_cluster_usage_limits(cluster_id, region)
   - Create serverless limit: create_serverless_usage_limit(workgroup_name, usage_type, amount, period, breach_action, region)
   - Migrate limits: migrate_usage_limits_to_serverless(cluster_id, workgroup_name, region, dry_run)
   - Note: Provisioned and serverless use different limit types (spectrum/concurrency-scaling vs RPU-hours)

Always ask clarifying questions:
- What's the cluster ID?
- What AWS region?
- Do they want to migrate data (snapshot) or just configuration?
- Do they have existing serverless resources?
- Do they want to migrate scheduled queries?
- Do they have cross-region snapshot copy enabled?
- Do they have usage limits configured?

When migrating scheduled queries:
- First list them to show what will be migrated
- Offer dry-run to preview changes
- Explain that queries will use Redshift Data API in serverless
- Mention that IAM role for EventBridge will be created if needed

When migrating maintenance and snapshot settings:
- Explain that serverless uses automatic maintenance windows (no manual window needed)
- Check if cross-region snapshot copy is enabled on the source cluster
- If enabled, configure it for the serverless namespace with the same destination region
- Maintenance track information is captured but serverless handles updates automatically

When migrating usage limits:
- Explain that provisioned and serverless use different limit types
- Provisioned: spectrum, concurrency-scaling, cross-region-datasharing
- Serverless: serverless-compute (measured in RPU-hours)
- Provide recommendations for equivalent serverless limits
- Offer dry-run to preview recommendations before creating limits

Be conversational, friendly, and explain technical concepts simply. Celebrate successful migrations!

Important Notes:
- --create-snapshot and --snapshot-name are mutually exclusive
- Default max-capacity is 512 RPU
- Price-performance target is set to level 50 (balanced)
- Both workgroup and namespace can have the same name as the cluster
"""


def create_agent():
    """Create and return the Redshift Migration agent."""
    # Use Claude Sonnet 4.5 via inference profile
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        temperature=0.3,  # Lower temperature for factual, helpful responses
        max_tokens=4096,
    )
    
    agent = Agent(
        model=model,
        tools=[
            # Universal AWS tool
            run_aws_command,
            # AWS inspection tools
            list_redshift_clusters,
            get_cluster_maintenance_settings,
            get_cluster_snapshot_copy_settings,
            get_cluster_usage_limits,
            # Migration-specific tools
            extract_cluster_config,
            migrate_cluster,
            apply_configuration,
            # Scheduled query tools
            list_scheduled_queries,
            migrate_scheduled_queries,
            # Serverless configuration tools
            configure_serverless_snapshot_copy,
            create_serverless_usage_limit,
            migrate_usage_limits_to_serverless,
            # Help system
            get_migration_help,
        ],
        system_prompt=SYSTEM_PROMPT,
    )
    
    return agent


def main():
    """Run the agent in interactive mode."""
    print("🚀 Redshift Migration Assistant")
    print("=" * 50)
    print("I'll help you migrate from Redshift Provisioned to Serverless.")
    print("Type 'exit' or 'quit' to end the conversation.\n")
    
    agent = create_agent()
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("\n👋 Goodbye! Happy migrating!")
                break
            
            if not user_input:
                continue
            
            print("\nAssistant: ", end="", flush=True)
            response = agent(user_input)
            print(response)
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye! Happy migrating!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    main()
