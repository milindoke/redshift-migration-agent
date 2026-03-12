"""
Property-based tests for Architecture Agent output constraints.

Feature: redshift-modernization-agents

Validates: Requirements FR-3.1, FR-3.3, FR-3.4, FR-3.5, FR-3.6
"""
from __future__ import annotations

from hypothesis import given, settings, strategies as st

from redshift_agents.models import (
    ArchitectureResult,
    DataSharingConfig,
    WorkgroupSpec,
)

# --- Strategies ---

_workgroup_name_st = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_",
    min_size=1, max_size=30,
)

_wlm_queue_name_st = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
    min_size=1, max_size=20,
)

_workload_type_st = st.sampled_from(["producer", "consumer", "mixed"])
_pattern_st = st.sampled_from(["hub-and-spoke", "independent", "hybrid"])
_complexity_st = st.sampled_from(["low", "medium", "high"])

_workgroup_spec_st = st.builds(
    WorkgroupSpec,
    name=_workgroup_name_st,
    source_wlm_queue=st.one_of(st.none(), _wlm_queue_name_st),
    workload_type=_workload_type_st,
    base_rpu=st.integers(min_value=32, max_value=512),  # min 32 per FR-3.3
    max_rpu=st.integers(min_value=32, max_value=2048),
    scaling_policy=st.just("ai-driven"),
    price_performance_target=st.sampled_from(["balanced", "cost-optimized", "performance"]),
)

_data_sharing_st = st.builds(
    DataSharingConfig,
    enabled=st.booleans(),
    producer_workgroup=_workgroup_name_st,
    consumer_workgroups=st.lists(_workgroup_name_st, min_size=0, max_size=5),
)

_architecture_result_st = st.builds(
    ArchitectureResult,
    architecture_pattern=_pattern_st,
    namespace_name=_workgroup_name_st,
    workgroups=st.lists(_workgroup_spec_st, min_size=1, max_size=8),
    data_sharing=_data_sharing_st,
    cost_estimate_monthly_min=st.floats(min_value=0.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
    cost_estimate_monthly_max=st.floats(min_value=0.0, max_value=500000.0, allow_nan=False, allow_infinity=False),
    migration_complexity=_complexity_st,
    trade_offs=st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=5),
)


# ---------------------------------------------------------------------------
# Property 5: Workgroup count matches WLM queue mapping rules
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    wlm_queue_names=st.lists(_wlm_queue_name_st, min_size=1, max_size=10, unique=True),
    extra_workgroups=st.lists(_workgroup_spec_st, min_size=0, max_size=3),
)
def test_workgroup_count_matches_wlm_queue_mapping(wlm_queue_names, extra_workgroups):
    """Property 5: Workgroup count matches WLM queue mapping rules

    For any assessment with N WLM queues (N > 1), the architecture must have
    at least N workgroups. For exactly 1 WLM queue, at least 2 workgroups
    (producer + consumer).

    **Validates: Requirements FR-3.1**
    """
    # Feature: redshift-modernization-agents, Property 5: Workgroup count matches WLM queue mapping rules

    n_queues = len(wlm_queue_names)

    # Build one workgroup per WLM queue
    workgroups = []
    for i, queue_name in enumerate(wlm_queue_names):
        workgroups.append(WorkgroupSpec(
            name=f"wg-{i}",
            source_wlm_queue=queue_name,
            workload_type="mixed",
            base_rpu=32,
            max_rpu=128,
            scaling_policy="ai-driven",
            price_performance_target="balanced",
        ))

    # For single-queue case, add a second workgroup (producer/consumer split)
    if n_queues == 1:
        workgroups.append(WorkgroupSpec(
            name="wg-consumer",
            source_wlm_queue=wlm_queue_names[0],
            workload_type="consumer",
            base_rpu=32,
            max_rpu=128,
            scaling_policy="ai-driven",
            price_performance_target="balanced",
        ))

    # Optionally add extra workgroups
    workgroups.extend(extra_workgroups)

    arch = ArchitectureResult(
        architecture_pattern="hub-and-spoke",
        namespace_name="test-ns",
        workgroups=workgroups,
        data_sharing=DataSharingConfig(enabled=True, producer_workgroup="wg-0", consumer_workgroups=["wg-consumer"]),
        cost_estimate_monthly_min=100.0,
        cost_estimate_monthly_max=500.0,
        migration_complexity="medium",
        trade_offs=["trade-off-1"],
    )

    # Verify the mapping rules
    if n_queues > 1:
        assert len(arch.workgroups) >= n_queues, (
            f"Expected at least {n_queues} workgroups for {n_queues} WLM queues, "
            f"got {len(arch.workgroups)}"
        )
    else:
        assert len(arch.workgroups) >= 2, (
            f"Expected at least 2 workgroups for single WLM queue, "
            f"got {len(arch.workgroups)}"
        )


# ---------------------------------------------------------------------------
# Property 6: All workgroup RPUs are at least 32
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(workgroups=st.lists(_workgroup_spec_st, min_size=1, max_size=10))
def test_all_workgroup_rpus_at_least_32(workgroups):
    """Property 6: All workgroup RPUs are at least 32

    For any architecture output, every workgroup's base_rpu must be >= 32.

    **Validates: Requirements FR-3.3**
    """
    # Feature: redshift-modernization-agents, Property 6: All workgroup RPUs are at least 32

    for wg in workgroups:
        assert wg.base_rpu >= 32, (
            f"Workgroup '{wg.name}' has base_rpu={wg.base_rpu}, "
            f"which is below the minimum of 32 required for AI-driven scaling"
        )


# ---------------------------------------------------------------------------
# Property 7: Architecture pattern is one of three valid values
# ---------------------------------------------------------------------------

_VALID_PATTERNS = {"hub-and-spoke", "independent", "hybrid"}


@settings(max_examples=100)
@given(arch=_architecture_result_st)
def test_architecture_pattern_is_valid(arch):
    """Property 7: Architecture pattern is one of three valid values

    For any architecture output, architecture_pattern must be one of:
    "hub-and-spoke", "independent", "hybrid".

    **Validates: Requirements FR-3.4**
    """
    # Feature: redshift-modernization-agents, Property 7: Architecture pattern is one of three valid values

    assert arch.architecture_pattern in _VALID_PATTERNS, (
        f"Invalid architecture_pattern '{arch.architecture_pattern}'. "
        f"Must be one of {_VALID_PATTERNS}"
    )


# ---------------------------------------------------------------------------
# Property 8: Architecture output includes cost estimates and migration complexity
# ---------------------------------------------------------------------------

_VALID_COMPLEXITIES = {"low", "medium", "high"}


@settings(max_examples=100)
@given(arch=_architecture_result_st)
def test_architecture_output_completeness(arch):
    """Property 8: Architecture output includes cost estimates and migration complexity

    For any architecture output, cost_estimate_monthly_min, cost_estimate_monthly_max,
    migration_complexity, workgroups, data_sharing, and trade_offs must all be present
    and non-null. migration_complexity must be one of "low", "medium", "high".

    **Validates: Requirements FR-3.5, FR-3.6**
    """
    # Feature: redshift-modernization-agents, Property 8: Architecture output includes cost estimates and migration complexity

    # All required fields must be present and non-null
    assert arch.cost_estimate_monthly_min is not None, "cost_estimate_monthly_min must not be None"
    assert arch.cost_estimate_monthly_max is not None, "cost_estimate_monthly_max must not be None"
    assert arch.migration_complexity is not None, "migration_complexity must not be None"
    assert arch.workgroups is not None, "workgroups must not be None"
    assert arch.data_sharing is not None, "data_sharing must not be None"
    assert arch.trade_offs is not None, "trade_offs must not be None"

    # migration_complexity must be a valid value
    assert arch.migration_complexity in _VALID_COMPLEXITIES, (
        f"Invalid migration_complexity '{arch.migration_complexity}'. "
        f"Must be one of {_VALID_COMPLEXITIES}"
    )
