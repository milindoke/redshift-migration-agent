"""Data models for Redshift configuration."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class IAMRoleConfig(BaseModel):
    """IAM role configuration."""
    role_arn: str
    is_default: bool = False


class VPCConfig(BaseModel):
    """VPC and network configuration."""
    vpc_id: str
    subnet_ids: List[str]
    security_group_ids: List[str]
    publicly_accessible: bool = False


class SnapshotSchedule(BaseModel):
    """Snapshot schedule configuration."""
    schedule_identifier: str
    schedule_definitions: List[str]
    tags: Dict[str, str] = Field(default_factory=dict)


class ScheduledQuery(BaseModel):
    """Scheduled query configuration."""
    rule_name: str
    schedule_expression: str
    query: str
    database: str
    enabled: bool = True


class LoggingConfig(BaseModel):
    """Logging configuration."""
    bucket_name: Optional[str] = None
    s3_key_prefix: Optional[str] = None
    log_exports: List[str] = Field(default_factory=list)


class ParameterGroupInfo(BaseModel):
    """Parameter group information."""
    name: str
    family: Optional[str] = None
    description: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    tags: Dict[str, str] = Field(default_factory=dict)


class UsageLimit(BaseModel):
    """Usage limit configuration."""
    limit_id: str
    feature_type: str  # spectrum, concurrency-scaling, cross-region-datasharing
    limit_type: str  # time, data-scanned
    amount: int
    period: str  # daily, weekly, monthly
    breach_action: str  # log, emit-metric, disable
    tags: Dict[str, str] = Field(default_factory=dict)


class ProvisionedClusterConfig(BaseModel):
    """Complete provisioned cluster configuration."""
    cluster_identifier: str
    iam_roles: List[IAMRoleConfig]
    vpc_config: VPCConfig
    snapshot_schedules: List[SnapshotSchedule] = Field(default_factory=list)
    scheduled_queries: List[ScheduledQuery] = Field(default_factory=list)
    logging_config: Optional[LoggingConfig] = None
    parameter_group_name: Optional[str] = None
    parameter_group_info: Optional[ParameterGroupInfo] = None
    maintenance_window: Optional[str] = None
    maintenance_track: Optional[str] = None
    snapshot_copy_config: Optional[Dict[str, Any]] = None
    usage_limits: List[UsageLimit] = Field(default_factory=list)
    tags: Dict[str, str] = Field(default_factory=dict)
    raw_config: Dict[str, Any] = Field(default_factory=dict)


class ServerlessWorkgroupConfig(BaseModel):
    """Serverless workgroup configuration to apply."""
    workgroup_name: str
    namespace_name: str
    iam_roles: List[str]
    subnet_ids: List[str]
    security_group_ids: List[str]
    publicly_accessible: bool = False
    config_parameters: List[Dict[str, str]] = Field(default_factory=list)
    tags: Dict[str, str] = Field(default_factory=dict)
