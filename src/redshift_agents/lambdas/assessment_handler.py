"""
Lambda handler for the Assessment action group.

Receives Bedrock Agent action group invocation events and dispatches to:
- listRedshiftClusters
- analyzeRedshiftCluster
- getClusterMetrics
- getWlmConfiguration

Requirements: 1.1, 1.3, 1.4, 1.5, 6.1, 6.2, 6.3
"""
from __future__ import annotations

import json
import os
import sys

# Ensure the Lambda package root is on sys.path so absolute imports work
# In Lambda: /var/task is the root, tools/ and models.py are at /var/task/tools/ etc.
# Locally: src/redshift_agents/ is the root
_this_dir = os.path.dirname(os.path.abspath(__file__))
_package_root = os.path.dirname(_this_dir)  # parent of lambdas/
if _package_root not in sys.path:
    sys.path.insert(0, _package_root)

from tools.redshift_tools import (
    analyze_redshift_cluster,
    get_cluster_metrics,
    get_wlm_configuration,
    list_redshift_clusters,
)


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


def handler(event: dict, context: object = None) -> dict:
    """Bedrock Agent action group Lambda handler for assessment tools."""
    try:
        api_path = event.get("apiPath", "")
        params = _parse_parameters(event)
        user_id = params.get("user_id", "")

        if api_path == "/listRedshiftClusters":
            result = list_redshift_clusters(
                region=params.get("region", ""),
                user_id=user_id,
            )
        elif api_path == "/analyzeRedshiftCluster":
            result = analyze_redshift_cluster(
                cluster_id=params["cluster_id"],
                region=params.get("region", ""),
                user_id=user_id,
            )
        elif api_path == "/getClusterMetrics":
            result = get_cluster_metrics(
                cluster_id=params["cluster_id"],
                region=params.get("region", ""),
                hours=int(params.get("hours", "24")),
                user_id=user_id,
            )
        elif api_path == "/getWlmConfiguration":
            result = get_wlm_configuration(
                cluster_id=params["cluster_id"],
                region=params.get("region", ""),
                user_id=user_id,
            )
        else:
            result = {"error": f"Unknown apiPath: {api_path}"}

        return _build_response(event, result)
    except Exception as exc:
        print(f"[assessment_handler] Unexpected error: {exc}", file=sys.stderr)
        return _build_response(event, {"error": f"Unexpected: {str(exc)}"})
