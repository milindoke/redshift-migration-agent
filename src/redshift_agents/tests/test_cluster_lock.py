"""
Property-based and unit tests for cluster locking mechanism.

Feature: redshift-modernization-agents

Validates: Requirements NFR-2.2, NFR-2.3
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from hypothesis import given, settings, strategies as st

from redshift_agents.tools.cluster_lock import acquire_lock, release_lock

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Identifiers: alphanumeric strings 1–40 chars (realistic cluster/user IDs)
_id_alphabet = st.characters(whitelist_categories=("L", "N"), min_codepoint=48, max_codepoint=122)
cluster_id_st = st.text(alphabet=_id_alphabet, min_size=1, max_size=40)
user_id_st = st.text(alphabet=_id_alphabet, min_size=1, max_size=40)


def _conditional_check_error() -> ClientError:
    """Build a ``ConditionalCheckFailedException`` ClientError."""
    return ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "Condition not met"}},
        "PutItem",
    )


# ---------------------------------------------------------------------------
# Property 16: Cluster lock mutual exclusion
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    cluster_id=cluster_id_st,
    user_a=user_id_st,
    user_b=user_id_st,
)
def test_cluster_lock_mutual_exclusion(cluster_id, user_a, user_b):
    """Property 16: Cluster lock mutual exclusion

    For any two concurrent lock acquisition attempts on the same cluster_id,
    exactly one must succeed and the other must fail.

    **Validates: Requirements NFR-2.2**
    """
    # Feature: redshift-modernization-agents, Property 16: Cluster lock mutual exclusion

    # Ensure two distinct users
    if user_a == user_b:
        user_b = user_b + "_other"

    mock_dynamodb = MagicMock()

    # First put_item succeeds; second raises ConditionalCheckFailedException
    mock_dynamodb.put_item.side_effect = [
        None,  # first caller wins
        _conditional_check_error(),  # second caller loses
    ]

    # get_item returns the first caller's lock info
    mock_dynamodb.get_item.return_value = {
        "Item": {
            "cluster_id": {"S": cluster_id},
            "lock_holder": {"S": user_a},
            "acquired_at": {"S": datetime.now(timezone.utc).isoformat()},
        }
    }

    with patch("redshift_agents.tools.cluster_lock.boto3.client", return_value=mock_dynamodb):
        result_a = acquire_lock(cluster_id, user_a)
        result_b = acquire_lock(cluster_id, user_b)

    # Exactly one acquired, the other denied
    assert result_a["acquired"] is True
    assert result_b["acquired"] is False

    # Winner stores correct holder info
    assert result_a["lock_holder"] == user_a
    assert "acquired_at" in result_a


# ---------------------------------------------------------------------------
# Property 17: Lock denial includes holder identity and timestamp
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    cluster_id=cluster_id_st,
    holder_user=user_id_st,
    requester_user=user_id_st,
)
def test_lock_denial_includes_holder_identity(cluster_id, holder_user, requester_user):
    """Property 17: Lock denial includes holder identity and timestamp

    For any failed lock acquisition attempt, the error response must include
    the current lock holder's lock_holder and acquired_at.

    **Validates: Requirements NFR-2.3**
    """
    # Feature: redshift-modernization-agents, Property 17: Lock denial includes holder identity and timestamp

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
        result = acquire_lock(cluster_id, requester_user)

    assert result["acquired"] is False
    assert result["lock_holder"] == holder_user
    assert result["acquired_at"] == acquired_at_iso


# ---------------------------------------------------------------------------
# Unit tests for cluster lock lifecycle
#
# Validates: Requirements NFR-2.2, NFR-2.3
# ---------------------------------------------------------------------------


class TestAcquireLockSuccess:
    """Test successful lock acquisition."""

    @patch("redshift_agents.tools.cluster_lock.boto3.client")
    def test_acquire_lock_success(self, mock_boto_client):
        """Successful put_item returns acquired=True with holder info."""
        mock_ddb = MagicMock()
        mock_ddb.put_item.return_value = {}
        mock_boto_client.return_value = mock_ddb

        result = acquire_lock("cluster-1", "alice")

        assert result["acquired"] is True
        assert result["cluster_id"] == "cluster-1"
        assert result["lock_holder"] == "alice"
        assert "acquired_at" in result
        # Verify ISO 8601 timestamp
        datetime.fromisoformat(result["acquired_at"])

        mock_boto_client.assert_called_once_with("dynamodb", region_name="us-east-2")
        mock_ddb.put_item.assert_called_once()


class TestAcquireLockContention:
    """Test lock contention (cluster already locked)."""

    @patch("redshift_agents.tools.cluster_lock.boto3.client")
    def test_acquire_lock_contention(self, mock_boto_client):
        """ConditionalCheckFailedException returns holder identity and timestamp."""
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

        result = acquire_lock("cluster-1", "alice")

        assert result["acquired"] is False
        assert result["cluster_id"] == "cluster-1"
        assert result["lock_holder"] == "bob"
        assert result["acquired_at"] == "2024-06-01T12:00:00+00:00"


class TestReleaseLock:
    """Test lock release scenarios."""

    @patch("redshift_agents.tools.cluster_lock.boto3.client")
    def test_release_lock_success(self, mock_boto_client):
        """Successful delete_item returns released=True."""
        mock_ddb = MagicMock()
        mock_ddb.delete_item.return_value = {}
        mock_boto_client.return_value = mock_ddb

        result = release_lock("cluster-1", "alice")

        assert result["released"] is True
        assert result["cluster_id"] == "cluster-1"

        mock_ddb.delete_item.assert_called_once()
        call_kwargs = mock_ddb.delete_item.call_args[1]
        assert call_kwargs["ConditionExpression"] == "lock_holder = :holder"

    @patch("redshift_agents.tools.cluster_lock.boto3.client")
    def test_release_lock_not_holder(self, mock_boto_client):
        """ConditionalCheckFailedException on delete returns released=False."""
        mock_ddb = MagicMock()
        mock_ddb.delete_item.side_effect = _conditional_check_error()
        mock_boto_client.return_value = mock_ddb

        result = release_lock("cluster-1", "eve")

        assert result["released"] is False
        assert "error" in result
        assert result["cluster_id"] == "cluster-1"

    @patch("redshift_agents.tools.cluster_lock.boto3.client")
    def test_release_lock_error_does_not_raise(self, mock_boto_client, capsys):
        """Release failure logs to stderr but never raises."""
        mock_ddb = MagicMock()
        mock_ddb.delete_item.side_effect = Exception("DynamoDB timeout")
        mock_boto_client.return_value = mock_ddb

        # Must not raise
        result = release_lock("cluster-1", "alice")

        assert result["released"] is False
        assert "DynamoDB timeout" in result["error"]

        captured = capsys.readouterr()
        assert "Failed to release lock" in captured.err


class TestAcquireLockDynamoDBError:
    """Test generic DynamoDB errors during acquisition."""

    @patch("redshift_agents.tools.cluster_lock.boto3.client")
    def test_acquire_lock_dynamodb_error(self, mock_boto_client):
        """Non-conditional DynamoDB error returns error dict."""
        mock_ddb = MagicMock()
        mock_ddb.put_item.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "Service unavailable"}},
            "PutItem",
        )
        mock_boto_client.return_value = mock_ddb

        result = acquire_lock("cluster-1", "alice")

        assert "error" in result
        assert result["cluster_id"] == "cluster-1"
        assert result["region"] == "us-east-2"
        # Should NOT have 'acquired' key — it's an error response
        assert "acquired" not in result
