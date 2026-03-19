"""
Redshift analysis and execution tools.

Plain Python functions that perform AWS API calls for cluster analysis,
serverless resource creation, data sharing, and query execution.
Each function accepts ``region`` and ``user_id`` for cross-region support
and identity propagation.
"""
from __future__ import annotations

import os
import time

from datetime import datetime, timedelta
from typing import Dict, List, Optional

import boto3

try:
    from tools.audit_logger import emit_audit_event
except ImportError:
    from .audit_logger import emit_audit_event



def _resolve_region(region: str) -> str:
    """Resolve region from parameter, env var, or default."""
    return region or os.getenv("AWS_REGION", "us-east-2")


def analyze_redshift_cluster(cluster_id: str, region: str = "", user_id: str = "") -> Dict:
    """
    Analyze Redshift cluster configuration and return detailed assessment.
    
    Args:
        cluster_id: Redshift cluster identifier
        region: AWS region where cluster is located (defaults to AWS_REGION env var)
        user_id: Identity of the person who initiated the request (for audit traceability)
        
    Returns:
        Dictionary with comprehensive cluster configuration details including:
        - Basic configuration (node type, count, status)
        - Security settings (encryption, VPC, public access)
        - Network configuration
        - Version information
        - Endpoint details
    """
    region = _resolve_region(region)

    redshift = boto3.client('redshift', region_name=region)
    
    emit_audit_event(
        "tool_invocation",
        "assessment",
        initiated_by=user_id,
        cluster_id=cluster_id,
        region=region,
        details={"tool": "analyze_redshift_cluster"},
    )
    
    try:
        response = redshift.describe_clusters(ClusterIdentifier=cluster_id)
        cluster = response['Clusters'][0]
        
        # Extract comprehensive cluster information
        cluster_info = {
            "cluster_identifier": cluster['ClusterIdentifier'],
            "node_type": cluster['NodeType'],
            "number_of_nodes": cluster['NumberOfNodes'],
            "cluster_status": cluster['ClusterStatus'],
            "cluster_version": cluster.get('ClusterVersion'),
            
            # Availability and location
            "availability_zone": cluster.get('AvailabilityZone'),
            "region": region,
            
            # Security configuration
            "encrypted": cluster.get('Encrypted', False),
            "kms_key_id": cluster.get('KmsKeyId'),
            "publicly_accessible": cluster.get('PubliclyAccessible', False),
            
            # Network configuration
            "vpc_id": cluster.get('VpcId'),
            "vpc_security_groups": [
                sg['VpcSecurityGroupId'] 
                for sg in cluster.get('VpcSecurityGroups', [])
            ],
            "enhanced_vpc_routing": cluster.get('EnhancedVpcRouting', False),
            
            # Endpoint information
            "endpoint_address": cluster.get('Endpoint', {}).get('Address'),
            "endpoint_port": cluster.get('Endpoint', {}).get('Port'),
            
            # Cluster configuration
            "cluster_parameter_group": cluster.get('ClusterParameterGroups', [{}])[0].get('ParameterGroupName'),
            "automated_snapshot_retention_period": cluster.get('AutomatedSnapshotRetentionPeriod'),
            "preferred_maintenance_window": cluster.get('PreferredMaintenanceWindow'),
            
            # Additional metadata
            "cluster_create_time": str(cluster.get('ClusterCreateTime')),
            "master_username": cluster.get('MasterUsername'),
            "db_name": cluster.get('DBName'),
        }
        
        return cluster_info
        
    except Exception as e:
        return {
            "error": str(e),
            "cluster_id": cluster_id,
            "region": region
        }


def get_cluster_metrics(
    cluster_id: str,
    region: str = "",
    hours: int = 24,
    user_id: str = "",
) -> Dict:
    """
    Get CloudWatch metrics for Redshift cluster performance analysis.
    
    Args:
        cluster_id: Redshift cluster identifier
        region: AWS region where cluster is located
        hours: Number of hours of historical data to retrieve (default: 24)
        user_id: Identity of the person who initiated the request (for audit traceability)
        
    Returns:
        Dictionary with performance metrics including:
        - CPU utilization statistics
        - Database connections
        - Network throughput
        - Disk space usage
        - Query performance indicators
    """
    region = _resolve_region(region)

    cloudwatch = boto3.client('cloudwatch', region_name=region)
    
    emit_audit_event(
        "tool_invocation",
        "assessment",
        initiated_by=user_id,
        cluster_id=cluster_id,
        region=region,
        details={"tool": "get_cluster_metrics", "hours": hours},
    )
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    metrics_to_fetch = [
        'CPUUtilization',
        'DatabaseConnections',
        'NetworkReceiveThroughput',
        'NetworkTransmitThroughput',
        'PercentageDiskSpaceUsed',
        'ReadLatency',
        'WriteLatency',
    ]
    
    metrics_data = {}
    
    try:
        for metric_name in metrics_to_fetch:
            response = cloudwatch.get_metric_statistics(
                Namespace='AWS/Redshift',
                MetricName=metric_name,
                Dimensions=[
                    {
                        'Name': 'ClusterIdentifier',
                        'Value': cluster_id
                    }
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour periods
                Statistics=['Average', 'Maximum', 'Minimum']
            )
            
            datapoints = response.get('Datapoints', [])
            if datapoints:
                # Calculate summary statistics
                averages = [dp['Average'] for dp in datapoints]
                metrics_data[metric_name] = {
                    'average': sum(averages) / len(averages) if averages else 0,
                    'maximum': max([dp['Maximum'] for dp in datapoints]),
                    'minimum': min([dp['Minimum'] for dp in datapoints]),
                    'datapoint_count': len(datapoints),
                    'period_hours': hours,
                }
            else:
                metrics_data[metric_name] = {
                    'error': 'No data available',
                    'period_hours': hours,
                }
        
        return {
            "cluster_id": cluster_id,
            "region": region,
            "time_range_hours": hours,
            "metrics": metrics_data,
            "timestamp": str(datetime.utcnow()),
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "cluster_id": cluster_id,
            "region": region
        }



def list_redshift_clusters(region: str = "", user_id: str = "") -> List[Dict] | Dict:
    """
    List all Redshift clusters in the specified region.

    Args:
        region: AWS region to list clusters from (defaults to AWS_REGION env var)
        user_id: Identity of the person who initiated the request (for audit traceability)

    Returns:
        List of dictionaries with basic cluster information for each cluster:
        - Cluster identifier
        - Node type and count
        - Status
        - Creation time
    """
    region = _resolve_region(region)

    redshift = boto3.client('redshift', region_name=region)

    emit_audit_event(
        "tool_invocation",
        "assessment",
        initiated_by=user_id,
        region=region,
        details={"tool": "list_redshift_clusters"},
    )

    try:
        response = redshift.describe_clusters()
        clusters = response.get('Clusters', [])

        cluster_list = []
        for cluster in clusters:
            cluster_list.append({
                "cluster_identifier": cluster['ClusterIdentifier'],
                "node_type": cluster['NodeType'],
                "number_of_nodes": cluster['NumberOfNodes'],
                "cluster_status": cluster['ClusterStatus'],
                "cluster_create_time": str(cluster.get('ClusterCreateTime')),
                "availability_zone": cluster.get('AvailabilityZone'),
                "encrypted": cluster.get('Encrypted', False),
                "publicly_accessible": cluster.get('PubliclyAccessible', False),
            })

        return cluster_list

    except Exception as e:
        return {
            "error": str(e),
            "region": region
        }


def get_wlm_configuration(
    cluster_id: str,
    region: str = "",
    user_id: str = "",
) -> Dict:
    """
    Query WLM configuration and per-queue metrics via the Redshift Data API.

    Args:
        cluster_id: Redshift cluster identifier
        region: AWS region where cluster is located (defaults to AWS_REGION env var)
        user_id: Identity of the person who initiated the request (for audit traceability)

    Returns:
        Dictionary with per-queue WLM metrics including:
        - queue_name, service_class, concurrency
        - queries_waiting, avg_wait_time_ms, avg_exec_time_ms
        - wait_to_exec_ratio, queries_spilling_to_disk, disk_spill_mb
        - saturation_pct
    """
    region = _resolve_region(region)

    redshift_data = boto3.client('redshift-data', region_name=region)

    emit_audit_event(
        "tool_invocation",
        "assessment",
        initiated_by=user_id,
        cluster_id=cluster_id,
        region=region,
        details={"tool": "get_wlm_configuration"},
    )

    sql = """
SELECT
    trim(cfg.name) AS queue_name,
    cfg.service_class,
    cfg.num_query_tasks AS concurrency,
    COALESCE(qs.queries_waiting, 0) AS queries_waiting,
    COALESCE(hist.avg_wait_time_ms, 0) AS avg_wait_time_ms,
    COALESCE(hist.avg_exec_time_ms, 0) AS avg_exec_time_ms,
    CASE
        WHEN COALESCE(hist.avg_exec_time_ms, 0) = 0 THEN 0.0
        ELSE ROUND(COALESCE(hist.avg_wait_time_ms, 0)::DECIMAL / hist.avg_exec_time_ms, 2)
    END AS wait_to_exec_ratio,
    COALESCE(spill.queries_spilling, 0) AS queries_spilling_to_disk,
    COALESCE(spill.total_spill_mb, 0.0) AS disk_spill_mb,
    CASE
        WHEN cfg.num_query_tasks = 0 THEN 0.0
        ELSE ROUND(COALESCE(qs.queries_running, 0)::DECIMAL / cfg.num_query_tasks * 100, 1)
    END AS saturation_pct
FROM STV_WLM_SERVICE_CLASS_CONFIG cfg
LEFT JOIN (
    SELECT service_class,
           SUM(CASE WHEN state = 'QueuedWaiting' THEN 1 ELSE 0 END) AS queries_waiting,
           SUM(CASE WHEN state = 'Executing' THEN 1 ELSE 0 END) AS queries_running
    FROM STV_WLM_QUERY_STATE
    GROUP BY service_class
) qs ON cfg.service_class = qs.service_class
LEFT JOIN (
    SELECT service_class,
           ROUND(AVG(total_queue_time) / 1000.0, 2) AS avg_wait_time_ms,
           ROUND(AVG(total_exec_time) / 1000.0, 2) AS avg_exec_time_ms
    FROM STL_WLM_QUERY
    WHERE total_exec_time > 0
    GROUP BY service_class
) hist ON cfg.service_class = hist.service_class
LEFT JOIN (
    SELECT service_class,
           COUNT(*) AS queries_spilling,
           ROUND(SUM(bytes_to_disk) / 1024.0 / 1024.0, 2) AS total_spill_mb
    FROM SVL_QUERY_SUMMARY
    WHERE bytes_to_disk > 0
    GROUP BY service_class
) spill ON cfg.service_class = spill.service_class
WHERE (cfg.service_class BETWEEN 6 AND 13 OR cfg.service_class BETWEEN 100 AND 107)
ORDER BY cfg.service_class
"""

    try:
        # Step 1: Execute the statement via Redshift Data API
        exec_resp = redshift_data.execute_statement(
            ClusterIdentifier=cluster_id,
            Database='dev',
            DbUser=user_id or None,
            Sql=sql,
        )
        statement_id = exec_resp['Id']

        # Step 2: Poll until the statement finishes
        max_wait_seconds = 30
        elapsed = 0
        while elapsed < max_wait_seconds:
            desc = redshift_data.describe_statement(Id=statement_id)
            status = desc['Status']
            if status == 'FINISHED':
                break
            if status == 'FAILED':
                return {
                    "error": desc.get('Error', 'Query failed'),
                    "cluster_id": cluster_id,
                    "region": region,
                }
            time.sleep(1)
            elapsed += 1

        if elapsed >= max_wait_seconds:
            return {
                "error": "Query timed out waiting for completion",
                "cluster_id": cluster_id,
                "region": region,
            }

        # Step 3: Fetch results
        result_resp = redshift_data.get_statement_result(Id=statement_id)
        records = result_resp.get('Records', [])

        queues = []
        for row in records:
            queues.append({
                "queue_name": row[0].get('stringValue', ''),
                "service_class": int(row[1].get('longValue', row[1].get('stringValue', 0))),
                "concurrency": int(row[2].get('longValue', row[2].get('stringValue', 0))),
                "queries_waiting": int(row[3].get('longValue', row[3].get('stringValue', 0))),
                "avg_wait_time_ms": float(row[4].get('longValue', row[4].get('doubleValue', row[4].get('stringValue', 0)))),
                "avg_exec_time_ms": float(row[5].get('longValue', row[5].get('doubleValue', row[5].get('stringValue', 0)))),
                "wait_to_exec_ratio": float(row[6].get('doubleValue', row[6].get('stringValue', 0.0))),
                "queries_spilling_to_disk": int(row[7].get('longValue', row[7].get('stringValue', 0))),
                "disk_spill_mb": float(row[8].get('doubleValue', row[8].get('stringValue', 0.0))),
                "saturation_pct": float(row[9].get('doubleValue', row[9].get('stringValue', 0.0))),
            })

        return {
            "cluster_id": cluster_id,
            "region": region,
            "wlm_queues": queues,
            "timestamp": str(datetime.utcnow()),
        }

    except Exception as e:
        return {
            "error": str(e),
            "cluster_id": cluster_id,
            "region": region,
        }

def create_cluster_snapshot(
    cluster_id: str,
    snapshot_identifier: str = "",
    region: str = "",
    user_id: str = "",
) -> Dict:
    """
    Create a manual snapshot of a Redshift cluster for migration.

    Args:
        cluster_id: Redshift cluster identifier
        snapshot_identifier: Name for the snapshot (auto-generated if empty)
        region: AWS region (defaults to AWS_REGION env var)
        user_id: Identity of the person who initiated the request

    Returns:
        Dictionary with snapshot details on success, or an error dict on failure.
    """
    region = _resolve_region(region)

    redshift = boto3.client('redshift', region_name=region)

    emit_audit_event(
        "tool_invocation",
        "execution",
        initiated_by=user_id,
        cluster_id=cluster_id,
        region=region,
        details={"tool": "create_cluster_snapshot"},
    )

    if not snapshot_identifier:
        from datetime import datetime
        ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        snapshot_identifier = f"{cluster_id}-migration-{ts}"

    try:
        response = redshift.create_cluster_snapshot(
            SnapshotIdentifier=snapshot_identifier,
            ClusterIdentifier=cluster_id,
            Tags=[
                {"Key": "created-by", "Value": "redshift-modernization-agent"},
                {"Key": "initiated-by", "Value": user_id},
            ],
        )
        snapshot = response.get("Snapshot", {})
        return {
            "snapshot_identifier": snapshot.get("SnapshotIdentifier"),
            "cluster_id": snapshot.get("ClusterIdentifier"),
            "status": snapshot.get("Status"),
            "snapshot_type": snapshot.get("SnapshotType"),
            "region": region,
        }
    except Exception as e:
        return {
            "error": str(e),
            "cluster_id": cluster_id,
            "region": region,
        }


def create_serverless_namespace(
    namespace_name: str,
    admin_username: str = "admin",
    db_name: str = "dev",
    region: str = "",
    user_id: str = "",
) -> Dict:
    """
    Create a Redshift Serverless namespace with admin credentials managed
    by AWS Secrets Manager.

    Args:
        namespace_name: Name for the new Serverless namespace
        admin_username: Admin user for the namespace (default: admin)
        db_name: Default database name (default: dev)
        region: AWS region where the namespace will be created (defaults to AWS_REGION env var)
        user_id: Identity of the person who initiated the request (for audit traceability)

    Returns:
        Dictionary with namespace details on success, or an error dict on failure.
    """
    region = _resolve_region(region)

    client = boto3.client('redshift-serverless', region_name=region)

    emit_audit_event(
        "tool_invocation",
        "execution",
        initiated_by=user_id,
        region=region,
        details={"tool": "create_serverless_namespace"},
    )

    try:
        response = client.create_namespace(
            namespaceName=namespace_name,
            adminUsername=admin_username,
            dbName=db_name,
            manageAdminPassword=True,
        )
        namespace = response.get("namespace", {})
        return {
            "namespace_name": namespace.get("namespaceName"),
            "namespace_id": namespace.get("namespaceId"),
            "namespace_arn": namespace.get("namespaceArn"),
            "status": namespace.get("status"),
            "admin_username": namespace.get("adminUsername"),
            "db_name": namespace.get("dbName"),
            "region": region,
        }
    except Exception as e:
        return {
            "error": str(e),
            "namespace_name": namespace_name,
            "region": region,
        }


def create_serverless_workgroup(
    workgroup_name: str,
    namespace_name: str,
    base_rpu: int = 32,
    max_rpu: int = 512,
    region: str = "",
    user_id: str = "",
) -> Dict:
    """
    Create a Redshift Serverless workgroup.

    Args:
        workgroup_name: Name for the new Serverless workgroup
        namespace_name: Name of the namespace to associate the workgroup with
        base_rpu: Base Redshift Processing Units (default: 32)
        max_rpu: Maximum Redshift Processing Units (default: 512)
        region: AWS region where the workgroup will be created (defaults to AWS_REGION env var)
        user_id: Identity of the person who initiated the request (for audit traceability)

    Returns:
        Dictionary with workgroup details on success, or an error dict on failure.
    """
    region = _resolve_region(region)

    client = boto3.client('redshift-serverless', region_name=region)

    emit_audit_event(
        "tool_invocation",
        "execution",
        initiated_by=user_id,
        region=region,
        details={"tool": "create_serverless_workgroup"},
    )

    try:
        response = client.create_workgroup(
            workgroupName=workgroup_name,
            namespaceName=namespace_name,
            baseCapacity=base_rpu,
            maxCapacity=max_rpu,
        )
        workgroup = response.get("workgroup", {})
        return {
            "workgroup_name": workgroup.get("workgroupName"),
            "workgroup_id": workgroup.get("workgroupId"),
            "workgroup_arn": workgroup.get("workgroupArn"),
            "status": workgroup.get("status"),
            "namespace_name": workgroup.get("namespaceName"),
            "base_capacity": workgroup.get("baseCapacity"),
            "max_capacity": workgroup.get("maxCapacity"),
            "region": region,
        }
    except Exception as e:
        return {
            "error": str(e),
            "workgroup_name": workgroup_name,
            "region": region,
        }


def execute_redshift_query(
    cluster_id: str,
    query: str,
    region: str = "",
    user_id: str = "",
) -> Dict:
    """
    Execute a SQL query against a Redshift cluster via the Redshift Data API.

    Identity propagation: the initiator's identity is passed as ``DbUser``
    so Redshift audit logs attribute the query to the individual, not just
    the IAM role (FR-5.3, NFR-7.1, NFR-7.3).

    Args:
        cluster_id: Redshift cluster identifier
        query: SQL query to execute
        region: AWS region where cluster is located (defaults to AWS_REGION env var)
        user_id: Identity of the person who initiated the request (for audit traceability)

    Returns:
        Dictionary with ``records`` key containing the query results, or
        ``error`` key on failure.
    """
    region = _resolve_region(region)

    redshift_data = boto3.client('redshift-data', region_name=region)

    emit_audit_event(
        "tool_invocation",
        "execution",
        initiated_by=user_id,
        cluster_id=cluster_id,
        region=region,
        details={"tool": "execute_redshift_query", "query": query},
    )

    try:
        # Step 1: Execute the statement via Redshift Data API
        exec_resp = redshift_data.execute_statement(
            ClusterIdentifier=cluster_id,
            Database='dev',
            DbUser=user_id or None,
            Sql=query,
        )
        statement_id = exec_resp['Id']

        # Step 2: Poll until the statement finishes
        max_wait_seconds = 30
        elapsed = 0
        while elapsed < max_wait_seconds:
            desc = redshift_data.describe_statement(Id=statement_id)
            status = desc['Status']
            if status == 'FINISHED':
                break
            if status == 'FAILED':
                return {
                    "error": desc.get('Error', 'Query failed'),
                    "cluster_id": cluster_id,
                    "region": region,
                }
            time.sleep(1)
            elapsed += 1

        if elapsed >= max_wait_seconds:
            return {
                "error": "Query timed out waiting for completion",
                "cluster_id": cluster_id,
                "region": region,
            }

        # Step 3: Fetch results
        result_resp = redshift_data.get_statement_result(Id=statement_id)
        records = result_resp.get('Records', [])

        return {
            "cluster_id": cluster_id,
            "region": region,
            "records": records,
        }

    except Exception as e:
        return {
            "error": str(e),
            "cluster_id": cluster_id,
            "region": region,
        }

def setup_data_sharing(
    producer_namespace: str,
    consumer_namespaces: str,
    datashare_name: str = "default_share",
    region: str = "",
    user_id: str = "",
) -> Dict:
    """
    Set up data sharing between a producer namespace and one or more consumer namespaces.

    Creates a datashare on the producer, adds the public schema and all its tables,
    then grants usage to each consumer namespace.

    Args:
        producer_namespace: Name of the producer Serverless namespace
        consumer_namespaces: Comma-separated list of consumer namespace names
        datashare_name: Name for the datashare (default: default_share)
        region: AWS region (defaults to AWS_REGION env var)
        user_id: Identity of the person who initiated the request (for audit traceability)

    Returns:
        Dictionary with datashare details on success, or an error dict on failure.
    """
    region = _resolve_region(region)

    emit_audit_event(
        "tool_invocation",
        "execution",
        initiated_by=user_id,
        region=region,
        details={"tool": "setup_data_sharing"},
    )

    try:
        serverless_client = boto3.client('redshift-serverless', region_name=region)
        redshift_data_client = boto3.client('redshift-data', region_name=region)

        # Resolve producer namespace ID
        producer_resp = serverless_client.get_namespace(namespaceName=producer_namespace)
        producer_ns = producer_resp.get("namespace", {})
        producer_ns_id = producer_ns.get("namespaceId", "")

        # Resolve consumer namespace IDs
        consumer_names = [n.strip() for n in consumer_namespaces.split(",") if n.strip()]
        consumer_ns_ids = []
        for name in consumer_names:
            resp = serverless_client.get_namespace(namespaceName=name)
            ns = resp.get("namespace", {})
            consumer_ns_ids.append({
                "name": name,
                "namespace_id": ns.get("namespaceId", ""),
            })

        # Execute SQL statements to create datashare and grant access
        sql_statements = [
            f"CREATE DATASHARE {datashare_name}",
            f"ALTER DATASHARE {datashare_name} ADD SCHEMA public",
            f"ALTER DATASHARE {datashare_name} ADD ALL TABLES IN SCHEMA public",
        ]
        for consumer in consumer_ns_ids:
            sql_statements.append(
                f"GRANT USAGE ON DATASHARE {datashare_name} TO NAMESPACE '{consumer['namespace_id']}'"
            )

        executed_statements = []
        for sql in sql_statements:
            exec_resp = redshift_data_client.execute_statement(
                WorkgroupName=producer_namespace,
                Database='dev',
                Sql=sql,
            )
            executed_statements.append({
                "sql": sql,
                "statement_id": exec_resp.get("Id", ""),
            })

        return {
            "datashare_name": datashare_name,
            "producer_namespace": producer_namespace,
            "producer_namespace_id": producer_ns_id,
            "consumer_namespaces": consumer_ns_ids,
            "statements_executed": len(executed_statements),
            "region": region,
        }
    except Exception as e:
        return {
            "error": str(e),
            "producer_namespace": producer_namespace,
            "region": region,
        }


def restore_snapshot_to_serverless(
    snapshot_identifier: str,
    namespace_name: str,
    workgroup_name: str = "",
    region: str = "",
    user_id: str = "",
) -> Dict:
    """
    Restore a Redshift cluster snapshot into a Serverless namespace.

    Args:
        snapshot_identifier: Identifier of the cluster snapshot to restore
        namespace_name: Target Serverless namespace name
        workgroup_name: Target Serverless workgroup name (optional)
        region: AWS region where the Serverless namespace resides
        user_id: Identity of the person who initiated the request (for audit traceability)

    Returns:
        Dictionary with restore details on success, or an error dict on failure.
    """
    region = _resolve_region(region)
    client = boto3.client('redshift-serverless', region_name=region)

    emit_audit_event(
        "tool_invocation",
        "execution",
        initiated_by=user_id,
        region=region,
        details={"tool": "restore_snapshot_to_serverless"},
    )

    try:
        kwargs = {
            "namespaceName": namespace_name,
            "snapshotName": snapshot_identifier,
        }
        if workgroup_name:
            kwargs["workgroupName"] = workgroup_name

        response = client.restore_from_snapshot(**kwargs)
        namespace = response.get("namespace", {})
        return {
            "namespace_name": namespace.get("namespaceName"),
            "namespace_id": namespace.get("namespaceId"),
            "namespace_arn": namespace.get("namespaceArn"),
            "status": namespace.get("status"),
            "snapshot_identifier": snapshot_identifier,
            "workgroup_name": workgroup_name,
            "region": region,
        }
    except Exception as e:
        return {
            "error": str(e),
            "snapshot_identifier": snapshot_identifier,
            "namespace_name": namespace_name,
            "region": region,
        }



