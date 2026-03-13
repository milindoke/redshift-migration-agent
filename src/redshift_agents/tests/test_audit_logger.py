"""
Tests for audit logger — emit_audit_event as standalone function.

Validates: Requirements 6.1, 6.4, 6.5, 14.1, 14.2, 14.5
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from hypothesis import given, settings, strategies as st

from redshift_agents.tools.audit_logger import (
    VALID_EVENT_TYPES,
    emit_audit_event,
)

# --- Strategies ---

event_type_st = st.sampled_from(sorted(VALID_EVENT_TYPES))
text_st = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S")),
    min_size=1,
    max_size=50,
)
details_st = st.fixed_dictionaries(
    {},
    optional={"key": st.text(min_size=0, max_size=20)},
)

REQUIRED_FIELDS = {
    "timestamp",
    "event_type",
    "agent_name",
    "customer_account_id",
    "initiated_by",
    "cluster_id",
    "region",
}


class _CaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.last_record = None

    def emit(self, record):
        self.last_record = record


@settings(max_examples=100)
@given(
    event_type=event_type_st,
    agent_name=text_st,
    customer_account_id=text_st,
    initiated_by=text_st,
    cluster_id=text_st,
    region=text_st,
    details=details_st,
)
def test_audit_event_schema_validity(
    event_type, agent_name, customer_account_id, initiated_by,
    cluster_id, region, details,
):
    """Property 14: Audit event schema validity

    **Validates: Requirements FR-5.4, NFR-6.2, NFR-6.6, NFR-7.2**
    """
    audit_logger = logging.getLogger("redshift_modernization_audit")
    handler = _CaptureHandler()
    audit_logger.addHandler(handler)

    try:
        emit_audit_event(
            event_type=event_type, agent_name=agent_name,
            customer_account_id=customer_account_id,
            initiated_by=initiated_by, cluster_id=cluster_id,
            region=region, details=details,
        )
        assert handler.last_record is not None
        record = handler.last_record
        for field in REQUIRED_FIELDS:
            assert hasattr(record, field), f"Missing: {field}"
        parsed = datetime.fromisoformat(record.timestamp)
        assert parsed.tzinfo is not None
        assert record.event_type in VALID_EVENT_TYPES
        assert record.agent_name == agent_name
        assert record.initiated_by == initiated_by
    finally:
        audit_logger.removeHandler(handler)


# --- Unit tests ---

class _CaptureHandlerUnit(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture()
def audit_capture():
    audit_logger = logging.getLogger("redshift_modernization_audit")
    h = _CaptureHandlerUnit()
    audit_logger.addHandler(h)
    yield h
    audit_logger.removeHandler(h)


@pytest.mark.parametrize("event_type", sorted(VALID_EVENT_TYPES))
def test_emit_each_valid_event_type(event_type, audit_capture):
    emit_audit_event(
        event_type=event_type, agent_name="test-agent",
        customer_account_id="123456789012", initiated_by="alice",
        cluster_id="cluster-1", region="us-east-2",
    )
    assert len(audit_capture.records) == 1
    assert audit_capture.records[0].event_type == event_type


def test_timestamp_iso8601_with_timezone(audit_capture):
    emit_audit_event(
        event_type="agent_start", agent_name="test-agent",
        customer_account_id="111111111111", initiated_by="bob",
        cluster_id="c-1", region="eu-west-1",
    )
    rec = audit_capture.records[0]
    parsed = datetime.fromisoformat(rec.timestamp)
    assert parsed.tzinfo is not None
    delta = abs((datetime.now(timezone.utc) - parsed).total_seconds())
    assert delta < 60


def test_account_id_uses_provided_value(audit_capture):
    emit_audit_event(
        event_type="tool_invocation", agent_name="a",
        customer_account_id="999888777666", initiated_by="u",
        cluster_id="c", region="us-east-1",
    )
    assert audit_capture.records[0].customer_account_id == "999888777666"


@patch.dict(os.environ, {"AWS_ACCOUNT_ID": "env-acct-123"})
def test_account_id_falls_back_to_env_var(audit_capture):
    emit_audit_event(
        event_type="workflow_start", agent_name="a",
        customer_account_id="", initiated_by="u",
        cluster_id="c", region="us-east-1",
    )
    assert audit_capture.records[0].customer_account_id == "env-acct-123"


@patch.dict(os.environ, {}, clear=True)
@patch("boto3.client")
def test_account_id_falls_back_to_sts(mock_boto_client, audit_capture):
    mock_sts = MagicMock()
    mock_sts.get_caller_identity.return_value = {"Account": "sts-acct-456"}
    mock_boto_client.return_value = mock_sts
    os.environ.pop("AWS_ACCOUNT_ID", None)
    os.environ.pop("AWS_REGION", None)
    emit_audit_event(
        event_type="workflow_complete", agent_name="a",
        customer_account_id="", initiated_by="u",
        cluster_id="c", region="us-west-2",
    )
    assert audit_capture.records[0].customer_account_id == "sts-acct-456"


@patch.dict(os.environ, {}, clear=True)
@patch("boto3.client", side_effect=Exception("no creds"))
def test_account_id_falls_back_to_unknown(mock_boto_client, audit_capture):
    os.environ.pop("AWS_ACCOUNT_ID", None)
    emit_audit_event(
        event_type="error", agent_name="a",
        customer_account_id="", initiated_by="u",
        cluster_id="c", region="us-east-1",
    )
    assert audit_capture.records[0].customer_account_id == "unknown"


def test_audit_failure_does_not_raise(capsys):
    audit_logger = logging.getLogger("redshift_modernization_audit")

    class _BrokenHandler(logging.Handler):
        def emit(self, record):
            raise RuntimeError("handler exploded")

    broken = _BrokenHandler()
    original = audit_logger.handlers[:]
    for h in original:
        audit_logger.removeHandler(h)
    audit_logger.addHandler(broken)
    try:
        emit_audit_event(
            event_type="agent_start", agent_name="a",
            customer_account_id="111", initiated_by="u",
            cluster_id="c", region="us-east-1",
        )
    finally:
        audit_logger.removeHandler(broken)
        for h in original:
            audit_logger.addHandler(h)
    captured = capsys.readouterr()
    assert "Failed to emit audit event" in captured.err


def test_details_defaults_to_empty_dict(audit_capture):
    emit_audit_event(
        event_type="phase_start", agent_name="test-agent",
        customer_account_id="123", initiated_by="u",
        cluster_id="c", region="us-east-1", details=None,
    )
    assert audit_capture.records[0].details == {}


def test_details_preserves_provided_dict(audit_capture):
    payload = {"tool": "list_clusters", "duration_ms": 42}
    emit_audit_event(
        event_type="tool_invocation", agent_name="test-agent",
        customer_account_id="123", initiated_by="u",
        cluster_id="c", region="us-east-1", details=payload,
    )
    assert audit_capture.records[0].details == payload
