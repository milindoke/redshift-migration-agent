"""
Cross-account log sharing opt-in for Redshift Modernization Agents.

During deployment/setup, the customer is prompted to opt-in to CloudWatch
cross-account log sharing with the Redshift Service Team. If opted in,
audit logs are shared via a CloudWatch Logs subscription filter.

CloudTrail captures underlying API calls regardless of opt-in (NFR-6.5).

Requirements: NFR-6.3, NFR-6.4, NFR-6.5
"""
from __future__ import annotations

import os
import sys
from typing import Dict

import boto3


LOG_GROUP_NAME = os.getenv(
    "AUDIT_LOG_GROUP", "/redshift-modernization/audit"
)
FILTER_NAME = "redshift-modernization-cross-account-share"


def configure_log_sharing(
    destination_arn: str,
    region: str = "us-east-2",
) -> Dict:
    """Configure CloudWatch Logs subscription filter for cross-account sharing.

    Args:
        destination_arn: ARN of the Redshift Service Team's log destination
        region: AWS region

    Returns:
        Dict with status or error
    """
    try:
        client = boto3.client("logs", region_name=region)
        client.put_subscription_filter(
            logGroupName=LOG_GROUP_NAME,
            filterName=FILTER_NAME,
            filterPattern="",  # all audit events
            destinationArn=destination_arn,
        )
        return {
            "status": "enabled",
            "log_group": LOG_GROUP_NAME,
            "destination_arn": destination_arn,
        }
    except Exception as exc:
        print(f"[log_sharing] Failed to configure: {exc}", file=sys.stderr)
        return {"error": str(exc)}


def remove_log_sharing(region: str = "us-east-2") -> Dict:
    """Remove the cross-account subscription filter."""
    try:
        client = boto3.client("logs", region_name=region)
        client.delete_subscription_filter(
            logGroupName=LOG_GROUP_NAME,
            filterName=FILTER_NAME,
        )
        return {"status": "disabled", "log_group": LOG_GROUP_NAME}
    except Exception as exc:
        print(f"[log_sharing] Failed to remove: {exc}", file=sys.stderr)
        return {"error": str(exc)}
