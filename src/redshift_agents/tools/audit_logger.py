"""
Structured audit logger for Redshift Modernization Agents.

Emits JSON-structured log events to a dedicated ``redshift_modernization_audit``
logger so the Redshift Service Team can query agent usage across the fleet using
CloudWatch Logs Insights.

Every audit event includes identity propagation (``initiated_by``) so the full
chain from user → agent → tool → Redshift is traceable.

Example CloudWatch Logs Insights query::

    fields @timestamp, customer_account_id, agent_name, event_type, initiated_by
    | filter event_type = "workflow_start"
    | stats count() by customer_account_id
    | sort count desc

Requirements: FR-5.4, NFR-6.1, NFR-6.2, NFR-6.6, NFR-7.2
"""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone

try:
    # python-json-logger v4+
    from pythonjsonlogger.json import JsonFormatter
except ImportError:
    # python-json-logger v2/v3
    from pythonjsonlogger import jsonlogger

    JsonFormatter = jsonlogger.JsonFormatter

from ..models import AuditEvent

# Valid event types per NFR-6.6
VALID_EVENT_TYPES = frozenset(
    {
        "agent_start",
        "tool_invocation",
        "workflow_start",
        "workflow_complete",
        "phase_start",
        "phase_complete",
        "error",
    }
)

# ---------------------------------------------------------------------------
# Logger setup — dedicated logger with JSON formatter
# ---------------------------------------------------------------------------

_logger = logging.getLogger("redshift_modernization_audit")

if not _logger.handlers:
    _handler = logging.StreamHandler()
    _formatter = JsonFormatter(
        fmt="%(timestamp)s %(event_type)s %(agent_name)s %(customer_account_id)s "
        "%(initiated_by)s %(cluster_id)s %(region)s",
        timestamp=False,  # we supply our own ISO 8601 timestamp
    )
    _handler.setFormatter(_formatter)
    _logger.addHandler(_handler)
    _logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Account ID resolution (best-effort)
# ---------------------------------------------------------------------------


def _resolve_account_id(provided: str) -> str:
    """Return *provided* if non-empty, else env var, else STS, else 'unknown'."""
    if provided:
        return provided

    env_val = os.getenv("AWS_ACCOUNT_ID", "")
    if env_val:
        return env_val

    try:
        import boto3

        return boto3.client("sts").get_caller_identity()["Account"]
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def emit_audit_event(
    event_type: str,
    agent_name: str,
    customer_account_id: str = "",
    initiated_by: str = "",
    cluster_id: str = "",
    region: str = "",
    details: dict | None = None,
) -> None:
    """Emit a structured JSON audit event.

    Failures are caught and logged to *stderr* so they never block the main
    workflow (NFR-6.1).

    Args:
        event_type: One of ``VALID_EVENT_TYPES``.
        agent_name: Agent that emitted the event (e.g. ``"assessment"``).
        customer_account_id: AWS account ID; resolved automatically if empty.
        initiated_by: ``user_id`` of the person who triggered the workflow.
        cluster_id: Target Redshift cluster identifier.
        region: AWS region of the target cluster.
        details: Arbitrary event-specific payload.
    """
    try:
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            agent_name=agent_name,
            customer_account_id=_resolve_account_id(customer_account_id),
            initiated_by=initiated_by,
            cluster_id=cluster_id,
            region=region or os.getenv("AWS_REGION", "us-east-2"),
            details=details or {},
        )

        _logger.info("audit_event", extra=asdict(event))
    except Exception:
        # Audit failures must never block the main workflow (NFR-6.1)
        logging.getLogger(__name__).error(
            "Failed to emit audit event", exc_info=True, extra={"stream": "stderr"}
        )
        print(
            f"[audit_logger] Failed to emit audit event: event_type={event_type}",
            file=sys.stderr,
        )
