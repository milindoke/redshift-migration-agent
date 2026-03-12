"""
Property-based tests for audit logger.

Feature: redshift-modernization-agents, Property 14: Audit event schema validity

Validates: Requirements FR-5.4, NFR-6.2, NFR-6.6, NFR-7.2
"""
from __future__ import annotations

import logging
import os
import sys
import types
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Bootstrap: add ``src/`` to sys.path so the full ``redshift_agents`` package
# is importable, and stub ``strands`` which is not installed in the test env.
# ---------------------------------------------------------------------------
_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

# Stub strands so tools/__init__.py → redshift_tools.py can be imported
_strands = types.ModuleType("strands")
_strands_tools = types.ModuleType("strands.tools")
_strands_tools.tool = lambda f: f  # no-op @tool decorator
_strands.tools = _strands_tools
sys.modules.setdefault("strands", _strands)
sys.modules.setdefault("strands.tools", _strands_tools)

from hypothesis import given, settings, strategies as st  # noqa: E402

from redshift_agents.tools.audit_logger import (  # noqa: E402
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
    """Logging handler that captures the last emitted log record."""

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
    event_type,
    agent_name,
    customer_account_id,
    initiated_by,
    cluster_id,
    region,
    details,
):
    """Property 14: Audit event schema validity

    For any audit event emitted by emit_audit_event, the event must contain all
    required fields (timestamp, event_type, agent_name, customer_account_id,
    initiated_by, cluster_id, region), the timestamp must be valid ISO 8601,
    and event_type must be one of the valid set.

    **Validates: Requirements FR-5.4, NFR-6.2, NFR-6.6, NFR-7.2**
    """
    # Feature: redshift-modernization-agents, Property 14: Audit event schema validity

    audit_logger = logging.getLogger("redshift_modernization_audit")
    handler = _CaptureHandler()
    audit_logger.addHandler(handler)

    try:
        emit_audit_event(
            event_type=event_type,
            agent_name=agent_name,
            customer_account_id=customer_account_id,
            initiated_by=initiated_by,
            cluster_id=cluster_id,
            region=region,
            details=details,
        )

        # The handler must have captured a record
        assert handler.last_record is not None, "No audit event was emitted"

        record = handler.last_record

        # All required fields must be present in the record's extra data
        for field in REQUIRED_FIELDS:
            assert hasattr(record, field), f"Missing required field: {field}"

        # Timestamp must be valid ISO 8601
        ts = record.timestamp
        parsed = datetime.fromisoformat(ts)
        assert parsed.tzinfo is not None, "Timestamp must be timezone-aware"

        # event_type must be one of the valid set
        assert record.event_type in VALID_EVENT_TYPES, (
            f"Invalid event_type: {record.event_type}"
        )

        # Verify the values match what was passed in
        assert record.agent_name == agent_name
        assert record.initiated_by == initiated_by
        assert record.cluster_id == cluster_id
        assert record.event_type == event_type
    finally:
        audit_logger.removeHandler(handler)


# ---------------------------------------------------------------------------
# Unit tests for audit logger
#
# Validates: Requirements NFR-6.2, NFR-6.6
# ---------------------------------------------------------------------------
import json
from unittest.mock import patch, MagicMock

import pytest


class _CaptureHandlerUnit(logging.Handler):
    """Logging handler that captures all emitted log records."""

    def __init__(self):
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture()
def audit_capture():
    """Attach a capture handler to the audit logger for the duration of a test."""
    audit_logger = logging.getLogger("redshift_modernization_audit")
    handler = _CaptureHandlerUnit()
    audit_logger.addHandler(handler)
    yield handler
    audit_logger.removeHandler(handler)


# --- 1. Each valid event type emits correctly ---

@pytest.mark.parametrize(
    "event_type",
    sorted(VALID_EVENT_TYPES),
)
def test_emit_each_valid_event_type(event_type, audit_capture):
    """Each valid event_type should produce a log record with matching type."""
    emit_audit_event(
        event_type=event_type,
        agent_name="test-agent",
        customer_account_id="123456789012",
        initiated_by="alice",
        cluster_id="cluster-1",
        region="us-east-2",
    )

    assert len(audit_capture.records) == 1
    rec = audit_capture.records[0]
    assert rec.event_type == event_type
    assert rec.agent_name == "test-agent"
    assert rec.customer_account_id == "123456789012"
    assert rec.initiated_by == "alice"
    assert rec.cluster_id == "cluster-1"


# --- 2. Timestamp is ISO 8601 with timezone ---

def test_timestamp_iso8601_with_timezone(audit_capture):
    """Timestamp must be valid ISO 8601 and include timezone info."""
    emit_audit_event(
        event_type="agent_start",
        agent_name="test-agent",
        customer_account_id="111111111111",
        initiated_by="bob",
        cluster_id="c-1",
        region="eu-west-1",
    )

    rec = audit_capture.records[0]
    parsed = datetime.fromisoformat(rec.timestamp)
    assert parsed.tzinfo is not None, "Timestamp must be timezone-aware"
    # Verify it's a reasonable recent time (within last minute)
    now = datetime.now(timezone.utc)
    delta = abs((now - parsed).total_seconds())
    assert delta < 60, f"Timestamp too far from now: {rec.timestamp}"


# --- 3. Missing/empty customer_account_id fallback chain ---

def test_account_id_uses_provided_value(audit_capture):
    """When customer_account_id is provided, it should be used directly."""
    emit_audit_event(
        event_type="tool_invocation",
        agent_name="a",
        customer_account_id="999888777666",
        initiated_by="u",
        cluster_id="c",
        region="us-east-1",
    )
    assert audit_capture.records[0].customer_account_id == "999888777666"


@patch.dict(os.environ, {"AWS_ACCOUNT_ID": "env-acct-123"})
def test_account_id_falls_back_to_env_var(audit_capture):
    """When customer_account_id is empty, fall back to AWS_ACCOUNT_ID env var."""
    emit_audit_event(
        event_type="workflow_start",
        agent_name="a",
        customer_account_id="",
        initiated_by="u",
        cluster_id="c",
        region="us-east-1",
    )
    assert audit_capture.records[0].customer_account_id == "env-acct-123"


@patch.dict(os.environ, {}, clear=True)
@patch("boto3.client")
def test_account_id_falls_back_to_sts(mock_boto_client, audit_capture):
    """When env var is absent, fall back to STS get_caller_identity."""
    mock_sts = MagicMock()
    mock_sts.get_caller_identity.return_value = {"Account": "sts-acct-456"}
    mock_boto_client.return_value = mock_sts

    # Ensure env vars don't interfere
    os.environ.pop("AWS_ACCOUNT_ID", None)
    os.environ.pop("AWS_REGION", None)

    emit_audit_event(
        event_type="workflow_complete",
        agent_name="a",
        customer_account_id="",
        initiated_by="u",
        cluster_id="c",
        region="us-west-2",
    )
    assert audit_capture.records[0].customer_account_id == "sts-acct-456"
    mock_boto_client.assert_called_once_with("sts")


@patch.dict(os.environ, {}, clear=True)
@patch("boto3.client", side_effect=Exception("no creds"))
def test_account_id_falls_back_to_unknown(mock_boto_client, audit_capture):
    """When both env var and STS fail, fall back to 'unknown'."""
    os.environ.pop("AWS_ACCOUNT_ID", None)

    emit_audit_event(
        event_type="error",
        agent_name="a",
        customer_account_id="",
        initiated_by="u",
        cluster_id="c",
        region="us-east-1",
    )
    assert audit_capture.records[0].customer_account_id == "unknown"


# --- 4. Audit logging failures don't raise (stderr fallback) ---

def test_audit_failure_does_not_raise(capsys):
    """If the audit logger itself fails, the exception must be swallowed and
    a message printed to stderr."""
    audit_logger = logging.getLogger("redshift_modernization_audit")

    class _BrokenHandler(logging.Handler):
        def emit(self, record):
            raise RuntimeError("handler exploded")

    broken = _BrokenHandler()
    # Remove all existing handlers so only the broken one is active
    original_handlers = audit_logger.handlers[:]
    for h in original_handlers:
        audit_logger.removeHandler(h)
    audit_logger.addHandler(broken)

    try:
        # Should NOT raise
        emit_audit_event(
            event_type="agent_start",
            agent_name="a",
            customer_account_id="111",
            initiated_by="u",
            cluster_id="c",
            region="us-east-1",
        )
    finally:
        audit_logger.removeHandler(broken)
        for h in original_handlers:
            audit_logger.addHandler(h)

    captured = capsys.readouterr()
    assert "Failed to emit audit event" in captured.err


# --- 5. details defaults to empty dict when None ---

def test_details_defaults_to_empty_dict(audit_capture):
    """When details=None, the emitted event should have details={}."""
    emit_audit_event(
        event_type="phase_start",
        agent_name="test-agent",
        customer_account_id="123",
        initiated_by="u",
        cluster_id="c",
        region="us-east-1",
        details=None,
    )
    assert audit_capture.records[0].details == {}


def test_details_preserves_provided_dict(audit_capture):
    """When details is provided, it should be passed through as-is."""
    payload = {"tool": "list_clusters", "duration_ms": 42}
    emit_audit_event(
        event_type="tool_invocation",
        agent_name="test-agent",
        customer_account_id="123",
        initiated_by="u",
        cluster_id="c",
        region="us-east-1",
        details=payload,
    )
    assert audit_capture.records[0].details == payload
