"""
DynamoDB-based cluster-level locking for Redshift Modernization Agents.

Prevents two users in the same account from working on the same Redshift
cluster simultaneously.  Lock acquisition uses a DynamoDB conditional write
(``attribute_not_exists``) for atomicity.  A 24-hour TTL provides a safety
net so stale locks are automatically cleaned up even if the orchestrator
crashes without releasing.

Requirements: NFR-2.2, NFR-2.3
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone
from typing import Dict

import boto3
from botocore.exceptions import ClientError

LOCK_TABLE = os.getenv("DYNAMODB_LOCK_TABLE", "redshift_modernization_locks")
TTL_SECONDS = 24 * 60 * 60  # 24 hours


def _resolve_region(region: str) -> str:
    """Resolve region from parameter, env var, or default."""
    return region or os.getenv("AWS_REGION", "us-east-2")


def acquire_lock(
    cluster_id: str,
    user_id: str,
    region: str = "",
) -> Dict:
    """Attempt to acquire a cluster-level lock.

    Uses a DynamoDB conditional put (``attribute_not_exists(cluster_id)``) so
    that exactly one caller wins when two requests race for the same cluster.

    Args:
        cluster_id: Redshift cluster identifier (DynamoDB partition key).
        user_id: Identity of the user requesting the lock.
        region: AWS region where the DynamoDB lock table resides.

    Returns:
        On success::

            {"acquired": True, "cluster_id": ..., "lock_holder": ..., "acquired_at": ...}

        On contention (cluster already locked)::

            {"acquired": False, "cluster_id": ..., "lock_holder": ..., "acquired_at": ...}

        On unexpected error::

            {"error": ..., "cluster_id": ..., "region": ...}
    """
    region = _resolve_region(region)
    now = datetime.now(timezone.utc)
    acquired_at = now.isoformat()
    ttl_epoch = int(time.time()) + TTL_SECONDS

    dynamodb = boto3.client("dynamodb", region_name=region)

    try:
        dynamodb.put_item(
            TableName=LOCK_TABLE,
            Item={
                "cluster_id": {"S": cluster_id},
                "lock_holder": {"S": user_id},
                "acquired_at": {"S": acquired_at},
                "ttl": {"N": str(ttl_epoch)},
            },
            ConditionExpression="attribute_not_exists(cluster_id)",
        )
        return {
            "acquired": True,
            "cluster_id": cluster_id,
            "lock_holder": user_id,
            "acquired_at": acquired_at,
        }
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            # Lock already held — fetch current holder info (NFR-2.3)
            try:
                resp = dynamodb.get_item(
                    TableName=LOCK_TABLE,
                    Key={"cluster_id": {"S": cluster_id}},
                )
                item = resp.get("Item", {})
                return {
                    "acquired": False,
                    "cluster_id": cluster_id,
                    "lock_holder": item.get("lock_holder", {}).get("S", "unknown"),
                    "acquired_at": item.get("acquired_at", {}).get("S", "unknown"),
                }
            except Exception:
                return {
                    "acquired": False,
                    "cluster_id": cluster_id,
                    "lock_holder": "unknown",
                    "acquired_at": "unknown",
                }
        return {
            "error": str(exc),
            "cluster_id": cluster_id,
            "region": region,
        }
    except Exception as exc:
        return {
            "error": f"Unexpected: {str(exc)}",
            "cluster_id": cluster_id,
            "region": region,
        }


def release_lock(
    cluster_id: str,
    user_id: str,
    region: str = "",
) -> Dict:
    """Release a cluster-level lock.

    Only the current lock holder can release the lock (enforced via a
    condition expression).  On failure the error is logged to *stderr*
    but never blocks — the 24-hour TTL acts as a safety net.

    Args:
        cluster_id: Redshift cluster identifier.
        user_id: Identity of the user releasing the lock.
        region: AWS region where the DynamoDB lock table resides.

    Returns:
        On success::

            {"released": True, "cluster_id": ...}

        On failure::

            {"released": False, "error": ..., "cluster_id": ...}
    """
    region = _resolve_region(region)
    dynamodb = boto3.client("dynamodb", region_name=region)

    try:
        dynamodb.delete_item(
            TableName=LOCK_TABLE,
            Key={"cluster_id": {"S": cluster_id}},
            ConditionExpression="lock_holder = :holder",
            ExpressionAttributeValues={":holder": {"S": user_id}},
        )
        return {"released": True, "cluster_id": cluster_id}
    except Exception as exc:
        # Release failures must never block the workflow (TTL safety net)
        print(
            f"[cluster_lock] Failed to release lock for {cluster_id}: {exc}",
            file=sys.stderr,
        )
        return {
            "released": False,
            "error": str(exc),
            "cluster_id": cluster_id,
        }
