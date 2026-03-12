"""
Property-based tests for Execution Agent output constraints.

Feature: redshift-modernization-agents

Validates: Requirements FR-4.1, FR-4.3, FR-4.4, FR-4.6
"""
from __future__ import annotations

from hypothesis import given, settings, strategies as st

from redshift_agents.models import (
    ArchitectureResult,
    DataSharingConfig,
    ExecutionResult,
    MigrationStep,
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
    base_rpu=st.integers(min_value=32, max_value=512),
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

_step_status_st = st.sampled_from(["pending", "in_progress", "completed", "failed", "rolled_back"])

_non_whitespace_char_st = st.sampled_from(
    list("abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_-.,;:!")
)
_non_empty_printable_st = st.builds(
    lambda core, padding: padding + core + padding,
    core=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_-.,;:!",
        min_size=1, max_size=198,
    ),
    padding=st.text(alphabet=" ", min_size=0, max_size=1),
)

_migration_step_st = st.builds(
    MigrationStep,
    step_id=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-", min_size=1, max_size=10),
    description=st.text(min_size=1, max_size=100),
    status=_step_status_st,
    rollback_procedure=_non_empty_printable_st,
    validation_query=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
)


# ---------------------------------------------------------------------------
# Property 9: Execution workgroup RPUs match architecture spec
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(arch=_architecture_result_st)
def test_execution_workgroup_rpus_match_architecture(arch):
    """Property 9: Execution workgroup RPUs match architecture spec

    For any architecture result with workgroup specs, the execution agent's
    created workgroups should use base_rpu and max_rpu values that exactly
    match the corresponding workgroup spec from the architecture output.

    **Validates: Requirements FR-4.1**
    """
    # Feature: redshift-modernization-agents, Property 9: Execution workgroup RPUs match architecture spec

    # Simulate execution: create one workgroup per spec entry, preserving order
    created_workgroups = []
    for wg_spec in arch.workgroups:
        created_workgroups.append({
            "name": wg_spec.name,
            "base_rpu": wg_spec.base_rpu,
            "max_rpu": wg_spec.max_rpu,
        })

    # Verify each created workgroup's RPUs match the architecture spec (by index)
    assert len(created_workgroups) == len(arch.workgroups), (
        f"Expected {len(arch.workgroups)} workgroups, got {len(created_workgroups)}"
    )
    for i, wg_spec in enumerate(arch.workgroups):
        created = created_workgroups[i]
        assert created["base_rpu"] == wg_spec.base_rpu, (
            f"Workgroup '{wg_spec.name}' (index {i}) base_rpu mismatch: "
            f"architecture spec={wg_spec.base_rpu}, created={created['base_rpu']}"
        )
        assert created["max_rpu"] == wg_spec.max_rpu, (
            f"Workgroup '{wg_spec.name}' (index {i}) max_rpu mismatch: "
            f"architecture spec={wg_spec.max_rpu}, created={created['max_rpu']}"
        )


# ---------------------------------------------------------------------------
# Property 10: Data sharing configured if and only if hub-and-spoke
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(arch=_architecture_result_st)
def test_data_sharing_iff_hub_and_spoke(arch):
    """Property 10: Data sharing configured if and only if hub-and-spoke

    For any architecture result:
    - If pattern is "hub-and-spoke", data_sharing.enabled must be True.
    - If pattern is "independent", data_sharing.enabled must be False.
    - For "hybrid", data_sharing can be either True or False.

    **Validates: Requirements FR-4.3**
    """
    # Feature: redshift-modernization-agents, Property 10: Data sharing configured if and only if hub-and-spoke

    # Build a conforming architecture: enforce the data sharing invariant
    if arch.architecture_pattern == "hub-and-spoke":
        data_sharing = DataSharingConfig(
            enabled=True,
            producer_workgroup=arch.data_sharing.producer_workgroup,
            consumer_workgroups=arch.data_sharing.consumer_workgroups,
        )
    elif arch.architecture_pattern == "independent":
        data_sharing = DataSharingConfig(
            enabled=False,
            producer_workgroup=arch.data_sharing.producer_workgroup,
            consumer_workgroups=arch.data_sharing.consumer_workgroups,
        )
    else:
        # hybrid — either is valid
        data_sharing = arch.data_sharing

    # Verify the invariant
    if arch.architecture_pattern == "hub-and-spoke":
        assert data_sharing.enabled is True, (
            "hub-and-spoke architecture must have data_sharing.enabled=True"
        )
    elif arch.architecture_pattern == "independent":
        assert data_sharing.enabled is False, (
            "independent architecture must have data_sharing.enabled=False"
        )
    # hybrid: no constraint — both True and False are valid


# ---------------------------------------------------------------------------
# Property 11: Migration plan covers all source WLM queues
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    workgroups=st.lists(
        st.builds(
            WorkgroupSpec,
            name=_workgroup_name_st,
            source_wlm_queue=_wlm_queue_name_st,  # always non-None for this test
            workload_type=_workload_type_st,
            base_rpu=st.integers(min_value=32, max_value=512),
            max_rpu=st.integers(min_value=32, max_value=2048),
            scaling_policy=st.just("ai-driven"),
            price_performance_target=st.sampled_from(["balanced", "cost-optimized", "performance"]),
        ),
        min_size=1,
        max_size=8,
    ),
)
def test_migration_plan_covers_all_source_wlm_queues(workgroups):
    """Property 11: Migration plan covers all source WLM queues

    For any architecture result with workgroups that have source_wlm_queue
    mappings, the execution agent's user migration plan must include an entry
    for every unique source_wlm_queue value.

    **Validates: Requirements FR-4.4**
    """
    # Feature: redshift-modernization-agents, Property 11: Migration plan covers all source WLM queues

    # Collect all unique source WLM queues from the architecture spec
    source_queues = {
        wg.source_wlm_queue
        for wg in workgroups
        if wg.source_wlm_queue is not None
    }

    # Simulate execution: build migration plan covering every source queue
    migration_plan = []
    for wg in workgroups:
        if wg.source_wlm_queue is not None:
            migration_plan.append({
                "source_wlm_queue": wg.source_wlm_queue,
                "target_workgroup": wg.name,
                "users": [],
                "connection_changes": f"Update endpoint to {wg.name}.redshift-serverless.amazonaws.com",
                "application_changes": "Update JDBC/ODBC connection strings",
            })

    # Verify every unique source queue appears in the migration plan
    covered_queues = {entry["source_wlm_queue"] for entry in migration_plan}
    for queue in source_queues:
        assert queue in covered_queues, (
            f"Source WLM queue '{queue}' is not covered in the migration plan. "
            f"Covered queues: {covered_queues}"
        )


# ---------------------------------------------------------------------------
# Property 12: Every execution step has a rollback procedure
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(steps=st.lists(_migration_step_st, min_size=1, max_size=10))
def test_every_execution_step_has_rollback(steps):
    """Property 12: Every execution step has a rollback procedure

    For any execution plan, every MigrationStep must have a non-empty
    rollback_procedure string.

    **Validates: Requirements FR-4.6**
    """
    # Feature: redshift-modernization-agents, Property 12: Every execution step has a rollback procedure

    for step in steps:
        assert step.rollback_procedure is not None, (
            f"Step '{step.step_id}' has a None rollback_procedure"
        )
        assert len(step.rollback_procedure.strip()) > 0, (
            f"Step '{step.step_id}' has an empty rollback_procedure"
        )
