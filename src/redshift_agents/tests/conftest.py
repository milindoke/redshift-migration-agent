"""
Shared test configuration and helpers for Bedrock Agents Lambda handler tests.

Provides ``build_action_group_event`` and ``parse_response_body`` helpers
used across all test files to construct Bedrock Agent action group invocation
events and parse Lambda handler responses.
"""
from __future__ import annotations

import json
import os
import sys

# Add src/ to sys.path so the full ``redshift_agents`` package is importable
_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)


def build_action_group_event(
    api_path: str,
    parameters: dict,
    action_group: str = "TestGroup",
    http_method: str = "GET",
) -> dict:
    """Construct a Bedrock Agent action group invocation event.

    Args:
        api_path: The API path for the action (e.g. ``/listRedshiftClusters``).
        parameters: Dict of parameter name -> value pairs.
        action_group: Action group name (default ``"TestGroup"``).
        http_method: HTTP method (default ``"GET"``).

    Returns:
        A dict matching the Bedrock Agent action group invocation event format.
    """
    return {
        "messageVersion": "1.0",
        "agent": {
            "name": "test-agent",
            "id": "test-id",
            "alias": "test-alias",
            "version": "1",
        },
        "actionGroup": action_group,
        "apiPath": api_path,
        "httpMethod": http_method,
        "parameters": [
            {"name": k, "type": "string", "value": str(v)}
            for k, v in parameters.items()
        ],
        "sessionAttributes": {},
        "promptSessionAttributes": {},
    }


def parse_response_body(response: dict):
    """Extract the parsed tool result from a Lambda handler response.

    Args:
        response: The dict returned by a Lambda handler.

    Returns:
        The parsed JSON body (dict or list).
    """
    body_str = response["response"]["responseBody"]["application/json"]["body"]
    return json.loads(body_str)
