"""Data models for Redshift Modernization Agents.

Defines structured dataclasses for assessment output, architecture output,
execution state, cluster locking, and audit events.

Requirements: FR-2.7, FR-3.7, FR-4.6
"""
from __future__ import annotations

from dataclasses import dataclass


# --- Assessment Output ---


@dataclass
class WLMQueueMetrics:
    """Per-queue WLM metrics from cluster assessment."""

    queue_name: str
    service_class: int
    concurrency: int
    queries_waiting: int
    avg_wait_time_ms: float
    avg_exec_time_ms: float
    wait_to_exec_ratio: float
    queries_spilling_to_disk: int
    disk_spill_mb: float
    saturation_pct: float


@dataclass
class ClusterSummary:
    """Redshift Provisioned cluster configuration summary."""

    cluster_id: str
    node_type: str
    number_of_nodes: int
    status: str
    region: str
    encrypted: bool
    vpc_id: str
    publicly_accessible: bool
    enhanced_vpc_routing: bool
    cluster_version: str


@dataclass
class AssessmentResult:
    """Complete output from the assessment agent."""

    cluster_summary: ClusterSummary
    wlm_queue_analysis: list[WLMQueueMetrics]
    contention_narrative: str
    cloudwatch_metrics: dict


# --- Architecture Output ---


@dataclass
class WorkgroupSpec:
    """Serverless workgroup specification from architecture design."""

    name: str
    source_wlm_queue: str | None
    workload_type: str  # "producer" | "consumer" | "mixed"
    base_rpu: int  # >= 32
    max_rpu: int
    scaling_policy: str  # "ai-driven"
    price_performance_target: str


@dataclass
class DataSharingConfig:
    """Data sharing configuration between workgroups."""

    enabled: bool
    producer_workgroup: str
    consumer_workgroups: list[str]


@dataclass
class ArchitectureResult:
    """Complete output from the architecture agent."""

    architecture_pattern: str  # "hub-and-spoke" | "independent" | "hybrid"
    namespace_name: str
    workgroups: list[WorkgroupSpec]
    data_sharing: DataSharingConfig
    cost_estimate_monthly_min: float
    cost_estimate_monthly_max: float
    migration_complexity: str  # "low" | "medium" | "high"
    trade_offs: list[str]


# --- Execution State ---


@dataclass
class MigrationStep:
    """A single step in the migration execution plan."""

    step_id: str
    description: str
    status: str  # "pending" | "in_progress" | "completed" | "failed" | "rolled_back"
    rollback_procedure: str
    validation_query: str | None


@dataclass
class ExecutionResult:
    """Complete output from the execution agent."""

    namespace_created: bool
    workgroups_created: list[str]
    snapshot_restored: bool
    data_sharing_configured: bool
    user_migration_plan: list[dict]
    performance_validation: dict  # query -> {provisioned_ms, serverless_ms, delta_pct}
    rollback_procedures: list[MigrationStep]
    cutover_plan: dict


# --- Cluster Locking ---


@dataclass
class ClusterLock:
    """DynamoDB-based cluster-level lock."""

    cluster_id: str  # DynamoDB partition key
    lock_holder: str  # user_id
    acquired_at: str  # ISO 8601
    ttl: int  # epoch seconds, 24h from acquisition


# --- Audit ---


@dataclass
class AuditEvent:
    """Structured audit event for fleet observability."""

    timestamp: str  # ISO 8601
    event_type: str  # agent_start | tool_invocation | workflow_start | workflow_complete | phase_start | phase_complete | error
    agent_name: str
    customer_account_id: str
    initiated_by: str  # user_id
    cluster_id: str
    region: str
    details: dict
