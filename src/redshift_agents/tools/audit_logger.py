"""
Structured audit logger for Redshift Modernization Agents.

Emits JSON-structured log events to CloudWatch Logs with a consistent schema
so the Redshift Service Team can query agent usage across the fleet using
CloudWatch Logs Insights.

All log events include:
- customer_account_id: Which customer account is using the agent
- agent_name: Which agent emitted the event
- event_type: Category of event (workflow_start, tool_invocation, phase_complete, etc.)
- cluster_id: Target Redshift cluster (when applicable)
- region: AWS region
- timestamp: ISO 8601 timestamp

The Redshift Service Team can query fleet-wide usage with CloudWatch Logs Insights:

    fields @timestamp, customer_account_id, agent_name, event_type, cluster_id
    | filter event_type = "workflow_start"
    | stats count() by customer_account_id
    | sort count desc

CloudTrail automatically captures the underlying Redshift/CloudWatch API calls
(DescribeClusters, GetMetricStatistics) with the caller's account ID. This audit
logger adds the agent-level context on top of that.
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional


# Use a dedicated logger name so CloudWatch log group filtering is easy
_logger = logging.getLogger("redshift_modernization_audit")


def _get_account_id() -> str:
    """Best-effort account ID from environment or STS."""
    acct = os.getenv("AWS_ACCOUNT_ID", "")
    if acct:
        return acct
    try:
        import boto3
        return boto3.client("sts").get_caller_identity()["Account"]
    except Exception:
        return "unknown"


def emit_audit_event(
    event_type: str,
    agent_name: str,
    *,
    customer_account_id: Optional[str] = None,
    cluster_id: Optional[str] = None,
    region: Optional[str] = None,
    workflow_phase: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Emit a structured audit log event.

    Args:
        event_type: One of: agent_start, workflow_start, workflow_complete,
                    tool_invocation, tool_result, phase_start, phase_complete,
                    scoring_result, error
        agent_name: e.g. "orchestrator", "assessment", "scoring", etc.
        customer_account_id: The customer account using the agent.
        cluster_id: Target Redshift cluster identifier.
        region: AWS region.
        workflow_phase: Current workflow phase (assessment, scoring, architecture, execution).
        details: Arbitrary key-value pairs for event-specific data.
    """
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "agent_name": agent_name,
        "customer_account_id": customer_account_id or _get_account_id(),
        "cluster_id": cluster_id or "",
        "region": region or os.getenv("AWS_REGION", "us-east-2"),
    }
    if workflow_phase:
        event["workflow_phase"] = workflow_phase
    if details:
        event["details"] = details

    # Emit as a single JSON line — CloudWatch Logs Insights can parse this natively
    _logger.info(json.dumps(event, default=str))
