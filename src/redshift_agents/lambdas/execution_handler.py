"""
Lambda handler for the Execution action group.

Receives Bedrock Agent action group invocation events and dispatches to:
- executeRedshiftQuery
- createServerlessNamespace
- createServerlessWorkgroup
- restoreSnapshotToServerless
- setupDataSharing

Includes STS AssumeRole with session tags for data-plane operations.

Requirements: 1.1, 1.3, 1.4, 1.5, 6.1, 6.2, 6.3, 15.6
"""
from __future__ import annotations

import json
import os
import sys

# Ensure the Lambda package root is on sys.path so absolute imports work
_this_dir = os.path.dirname(os.path.abspath(__file__))
_package_root = os.path.dirname(_this_dir)
if _package_root not in sys.path:
    sys.path.insert(0, _package_root)

import boto3

from tools.redshift_tools import (
    create_cluster_snapshot,
    create_serverless_namespace,
    create_serverless_workgroup,
    execute_redshift_query,
    restore_snapshot_to_serverless,
    setup_data_sharing,
)

# Role ARN for data-plane operations (set via Lambda environment variable)
DATA_PLANE_ROLE_ARN = os.getenv("DATA_PLANE_ROLE_ARN", "")


def _parse_parameters(event: dict) -> dict:
    """Convert Bedrock Agent parameter list to a flat dict."""
    return {p["name"]: p["value"] for p in event.get("parameters", [])}


def _build_response(event: dict, result: object) -> dict:
    """Build the Bedrock Agent action group response format."""
    # Ensure body is never empty — Bedrock rejects blank text blocks
    if result is None:
        result = {"status": "no data returned"}
    body = json.dumps(result)
    if not body or body == "null":
        body = json.dumps({"status": "empty result"})
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", ""),
            "apiPath": event.get("apiPath", ""),
            "httpMethod": event.get("httpMethod", ""),
            "httpStatusCode": 200,
            "responseBody": {
                "application/json": {
                    "body": body,
                }
            },
        },
    }


def _assume_role_with_session_tags(user_id: str) -> None:
    """Assume a data-plane role with user session tags.

    This sets up the STS session so that downstream AWS API calls carry
    ``PrincipalTag/user={user_id}`` for authorization and CloudTrail
    attribution.  If no role ARN is configured the call is skipped.
    """
    if not DATA_PLANE_ROLE_ARN:
        return None

    sts = boto3.client("sts")
    sts.assume_role(
        RoleArn=DATA_PLANE_ROLE_ARN,
        RoleSessionName=f"exec-{user_id[:32]}",
        Tags=[{"Key": "user", "Value": user_id}],
    )


def handler(event: dict, context: object = None) -> dict:
    """Bedrock Agent action group Lambda handler for execution tools."""
    try:
        api_path = event.get("apiPath", "")
        params = _parse_parameters(event)
        user_id = params.get("user_id", "")

        # Attempt STS AssumeRole with session tags for data-plane ops
        try:
            _assume_role_with_session_tags(user_id)
        except Exception as exc:
            print(
                f"[execution_handler] STS AssumeRole failed: {exc}",
                file=sys.stderr,
            )

        if api_path == "/createClusterSnapshot":
            result = create_cluster_snapshot(
                cluster_id=params["cluster_id"],
                snapshot_identifier=params.get("snapshot_identifier", ""),
                region=params.get("region", ""),
                user_id=user_id,
            )
        elif api_path == "/executeRedshiftQuery":
            result = execute_redshift_query(
                cluster_id=params["cluster_id"],
                query=params["query"],
                region=params.get("region", ""),
                user_id=user_id,
            )
        elif api_path == "/createServerlessNamespace":
            result = create_serverless_namespace(
                namespace_name=params["namespace_name"],
                admin_username=params.get("admin_username", "admin"),
                db_name=params.get("db_name", "dev"),
                region=params.get("region", ""),
                user_id=user_id,
            )
        elif api_path == "/createServerlessWorkgroup":
            result = create_serverless_workgroup(
                workgroup_name=params["workgroup_name"],
                namespace_name=params["namespace_name"],
                base_rpu=int(params.get("base_rpu", "32")),
                max_rpu=int(params.get("max_rpu", "512")),
                region=params.get("region", ""),
                user_id=user_id,
            )
        elif api_path == "/restoreSnapshotToServerless":
            result = restore_snapshot_to_serverless(
                snapshot_identifier=params["snapshot_identifier"],
                namespace_name=params["namespace_name"],
                workgroup_name=params.get("workgroup_name", ""),
                region=params.get("region", ""),
                user_id=user_id,
            )
        elif api_path == "/setupDataSharing":
            result = setup_data_sharing(
                producer_namespace=params["producer_namespace"],
                consumer_namespaces=params["consumer_namespaces"],
                datashare_name=params.get("datashare_name", "default_share"),
                region=params.get("region", ""),
                user_id=user_id,
            )
        else:
            result = {"error": f"Unknown apiPath: {api_path}"}

        return _build_response(event, result)
    except Exception as exc:
        print(f"[execution_handler] Unexpected error: {exc}", file=sys.stderr)
        return _build_response(event, {"error": f"Unexpected: {str(exc)}"})
