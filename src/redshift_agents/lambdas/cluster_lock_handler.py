"""
Lambda handler for the Cluster Lock action group.

Receives Bedrock Agent action group invocation events and dispatches to:
- acquireClusterLock
- releaseClusterLock

Requirements: 1.1, 7.1, 7.2, 7.3, 7.5
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

from tools.cluster_lock import acquire_lock, release_lock


def _parse_parameters(event: dict) -> dict:
    """Convert Bedrock Agent parameter list to a flat dict."""
    return {p["name"]: p["value"] for p in event.get("parameters", [])}


def _build_response(event: dict, result: object) -> dict:
    """Build the Bedrock Agent action group response format."""
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", ""),
            "apiPath": event.get("apiPath", ""),
            "httpMethod": event.get("httpMethod", ""),
            "httpStatusCode": 200,
            "responseBody": {
                "application/json": {
                    "body": json.dumps(result),
                }
            },
        },
    }


def handler(event: dict, context: object = None) -> dict:
    """Bedrock Agent action group Lambda handler for cluster lock operations."""
    try:
        api_path = event.get("apiPath", "")
        params = _parse_parameters(event)
        user_id = params.get("user_id", "")

        if api_path == "/acquireClusterLock":
            result = acquire_lock(
                cluster_id=params["cluster_id"],
                user_id=user_id,
                region=params.get("region", "us-east-1"),
            )
        elif api_path == "/releaseClusterLock":
            result = release_lock(
                cluster_id=params["cluster_id"],
                user_id=user_id,
                region=params.get("region", "us-east-1"),
            )
        else:
            result = {"error": f"Unknown apiPath: {api_path}"}

        return _build_response(event, result)
    except Exception as exc:
        print(f"[cluster_lock_handler] Unexpected error: {exc}", file=sys.stderr)
        return _build_response(event, {"error": f"Unexpected: {str(exc)}"})
