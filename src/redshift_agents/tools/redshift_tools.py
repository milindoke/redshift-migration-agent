"""
Redshift analysis tools using Strands @tool decorator.

These tools will be available to subagents for cluster analysis.
"""
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from strands.tools import tool


@tool
def analyze_redshift_cluster(cluster_id: str, region: str = "us-east-2") -> Dict:
    """
    Analyze Redshift cluster configuration and return detailed assessment.
    
    Args:
        cluster_id: Redshift cluster identifier
        region: AWS region where cluster is located (default: us-east-2)
        
    Returns:
        Dictionary with comprehensive cluster configuration details including:
        - Basic configuration (node type, count, status)
        - Security settings (encryption, VPC, public access)
        - Network configuration
        - Version information
        - Endpoint details
    """
    redshift = boto3.client('redshift', region_name=region)
    
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


@tool
def get_cluster_metrics(
    cluster_id: str,
    region: str = "us-east-2",
    hours: int = 24
) -> Dict:
    """
    Get CloudWatch metrics for Redshift cluster performance analysis.
    
    Args:
        cluster_id: Redshift cluster identifier
        region: AWS region where cluster is located
        hours: Number of hours of historical data to retrieve (default: 24)
        
    Returns:
        Dictionary with performance metrics including:
        - CPU utilization statistics
        - Database connections
        - Network throughput
        - Disk space usage
        - Query performance indicators
    """
    cloudwatch = boto3.client('cloudwatch', region_name=region)
    
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


@tool
def list_redshift_clusters(region: str = "us-east-2") -> List[Dict]:
    """
    List all Redshift clusters in the specified region.
    
    Args:
        region: AWS region to list clusters from (default: us-east-2)
        
    Returns:
        List of dictionaries with basic cluster information for each cluster:
        - Cluster identifier
        - Node type and count
        - Status
        - Creation time
    """
    redshift = boto3.client('redshift', region_name=region)
    
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
        return [{
            "error": str(e),
            "region": region
        }]
