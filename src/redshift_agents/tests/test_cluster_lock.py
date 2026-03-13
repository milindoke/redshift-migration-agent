"""
Tests for cluster lock Lambda handler with action group events.

Validates: Requirements 7.1, 7.2, 7.3, 11.1, 11.5
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from hypothesis import given, settings, strategies as st

from redshift_agents.lambdas.cluster_lock_handler import handler as lock_handler
from redshift_agents.tests.conftest import build_action_group_event, parse_response_body

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_id_alphabet = st.characters(whitelist_categories=("L", "N"), min_codepoint=48, max_codepoint=122)
cluster_id_st = st.text(alphabet=_id_alphabet, min_size=1, max_size=40)
user_id_st = st.text(alphabet=_id_alphabet, min_size=1, max_size=40)


def _conditional_check_error() -> ClientError:
    return ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "Condition not met"}},
        "PutItem",
    )


# ---------------------------------------------------------------------------
# Property 16: Cluster lock mutual exclusion (via Lambda handler)
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(cluster_id=cluster_id_st, user_a=user_id_st, user_b=user_id_st)
def test_cluster_lock_mutual_exclusion(cluster_id, user_a, user_b):
    """Property 16: Cluster lock mutual exclusion

    **Validates: Requirements NFR-2.2**
    """
    if user_a == user_b:
        user_b = user_b + "_other"

    mock_dynamodb = MagicMock()
    mock_dynamodb.put_item.side_effect = [
        None,
        _conditional_check_error(),
    ]
    mock_dynamodb.get_item.return_value = {
        "Item": {
            "cluster_id": {"S": cluster_id},
            "lock_holder": {"S": user_a},
            "acquired_at": {"S": datetime.now(timezone.utc).isoformat()},
        }
    }

    with patch("redshift_agents.tools.cluster_lock.boto3.client", return_value=mock_dynamodb):
        event_a = build_action_group_event(
            "/acquireClusterLock",
            {"cluster_id": cluster_id, "user_id": user_a, "region": "us-east-2"},
        )
        resp_a = lock_handler(event_a)
        result_a = parse_response_body(resp_a)

        event_b = build_action_group_event(
            "/acquireClusterLock",
            {"cluster_id": cluster_id, "user_id": user_b, "region": "us-east-2"},
        )
        resp_b = lock_handler(event_b)
        result_b = parse_response_body(resp_b)

    assert result_a["acquired"] is True
    assert result_b["acquired"] is False
    assert result_a["lock_holder"] == user_a


# ---------------------------------------------------------------------------
# Property 17: Lock denial includes holder identity and timestamp
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(cluster_id=cluster_id_st, holder_user=user_id_st, requester_user=user_id_st)
def test_lock_denial_includes_holder_identity(cluster_id, holder_user, requester_user):
    """Property 17: Lock denial includes holder identity and timestamp

    **Validates: Requirements NFR-2.3**
    """
    if holder_user == requester_user:
        requester_user = requester_user + "_req"

    acquired_at_iso = datetime.now(timezone.utc).isoformat()

    mock_dynamodb = MagicMock()
    mock_dynamodb.put_item.side_effect = _conditional_check_error()
    mock_dynamodb.get_item.return_value = {
        "Item": {
            "cluster_id": {"S": cluster_id},
            "lock_holder": {"S": holder_user},
            "acquired_at": {"S": acquired_at_iso},
        }
    }

    with patch("redshift_agents.tools.cluster_lock.boto3.client", return_value=mock_dynamodb):
        event = build_action_group_event(
            "/acquireClusterLock",
            {"cluster_id": cluster_id, "user_id": requester_user, "region": "us-east-2"},
        )
        resp = lock_handler(event)
        result = parse_response_body(resp)

    assert result["acquired"] is False
    assert result["lock_holder"] == holder_user
    assert result["acquired_at"] == acquired_at_iso


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


class TestAcquireLockSuccess:
    @patch("redshift_agents.tools.cluster_lock.boto3.client")
    def test_acquire_lock_success(self, mock_boto_client):
        mock_ddb = MagicMock()
        mock_ddb.put_item.return_value = {}
        mock_boto_client.return_value = mock_ddb

        event = build_action_group_event(
            "/acquireClusterLock",
            {"cluster_id": "cluster-1", "user_id": "alice", "region": "us-east-2"},
        )
        resp = lock_handler(event)
        result = parse_response_body(resp)

        assert result["acquired"] is True
        assert result["cluster_id"] == "cluster-1"
        assert result["lock_holder"] == "alice"
        datetime.fromisoformat(result["acquired_at"])


class TestAcquireLockContention:
    @patch("redshift_agents.tools.cluster_lock.boto3.client")
    def test_acquire_lock_contention(self, mock_boto_client):
        mock_ddb = MagicMock()
        mock_ddb.put_item.side_effect = _conditional_check_error()
        mock_ddb.get_item.return_value = {
            "Item": {
                "cluster_id": {"S": "cluster-1"},
                "lock_holder": {"S": "bob"},
                "acquired_at": {"S": "2024-06-01T12:00:00+00:00"},
            }
        }
        mock_boto_client.return_value = mock_ddb

        event = build_action_group_event(
            "/acquireClusterLock",
            {"cluster_id": "cluster-1", "user_id": "alice", "region": "us-east-2"},
        )
        resp = lock_handler(event)
        result = parse_response_body(resp)

        assert result["acquired"] is False
        assert result["lock_holder"] == "bob"


class TestReleaseLock:
    @patch("redshift_agents.tools.cluster_lock.boto3.client")
    def test_release_lock_success(self, mock_boto_client):
        mock_ddb = MagicMock()
        mock_ddb.delete_item.return_value = {}
        mock_boto_client.return_value = mock_ddb

        event = build_action_group_event(
            "/releaseClusterLock",
            {"cluster_id": "cluster-1", "user_id": "alice", "region": "us-east-2"},
        )
        resp = lock_handler(event)
        result = parse_response_body(resp)
        assert result["released"] is True

    @patch("redshift_agents.tools.cluster_lock.boto3.client")
    def test_release_lock_not_holder(self, mock_boto_client):
        mock_ddb = MagicMock()
        mock_ddb.delete_item.side_effect = _conditional_check_error()
        mock_boto_client.return_value = mock_ddb

        event = build_action_group_event(
            "/releaseClusterLock",
            {"cluster_id": "cluster-1", "user_id": "eve", "region": "us-east-2"},
        )
        resp = lock_handler(event)
        result = parse_response_body(resp)
        assert result["released"] is False
        assert "error" in result

    @patch("redshift_agents.tools.cluster_lock.boto3.client")
    def test_release_lock_error_does_not_raise(self, mock_boto_client, capsys):
        mock_ddb = MagicMock()
        mock_ddb.delete_item.side_effect = Exception("DynamoDB timeout")
        mock_boto_client.return_value = mock_ddb

        event = build_action_group_event(
            "/releaseClusterLock",
            {"cluster_id": "cluster-1", "user_id": "alice", "region": "us-east-2"},
        )
        resp = lock_handler(event)
        result = parse_response_body(resp)
        assert result["released"] is False
        captured = capsys.readouterr()
        assert "Failed to release lock" in captured.err


class TestAcquireLockDynamoDBError:
    @patch("redshift_agents.tools.cluster_lock.boto3.client")
    def test_acquire_lock_dynamodb_error(self, mock_boto_client):
        mock_ddb = MagicMock()
        mock_ddb.put_item.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "Service unavailable"}},
            "PutItem",
        )
        mock_boto_client.return_value = mock_ddb

        event = build_action_group_event(
            "/acquireClusterLock",
            {"cluster_id": "cluster-1", "user_id": "alice", "region": "us-east-2"},
        )
        resp = lock_handler(event)
        result = parse_response_body(resp)
        assert "error" in result
        assert "acquired" not in result
