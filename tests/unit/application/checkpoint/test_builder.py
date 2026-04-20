from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from tallylot.domain.assertion import QuantityValue
from tallylot.domain.checkpoint import (
    CheckpointAssertionContinuityKind,
    CheckpointAssertionTrustLevel,
)
from tallylot.domain.reconciliation import (
    BalanceTargetKind,
    BalanceTargetObservationStatus,
    BalanceTargetRecord,
    CheckpointProposalRecord,
    CheckpointProposalStatus,
    ComparisonOutcome,
    ContinuitySegmentRecord,
    ContinuitySegmentStatus,
    ReconciliationState,
)

from tallylot.application.checkpoint import build_checkpoints


def test_builder_emits_one_assertion_per_ready_proposal() -> None:
    states = (_ready_state(),)

    checkpoints = build_checkpoints(reconciliation_states=states)

    assert len(checkpoints) == 1
    assert len(checkpoints[0].checkpoint_assertion_records) == 1
    assert (
        checkpoints[0].checkpoint_assertion_records[0].trust_level
        is CheckpointAssertionTrustLevel.FILING_READY
    )


def test_builder_groups_multiple_state_refs_at_one_as_of_into_one_checkpoint() -> None:
    first = _ready_state(state_id="state-1")
    second = _ready_state(
        state_id="state-2",
        subject_ref=(
            "position",
            (
                ("beneficial_owner:filing",),
                ("location:coinbase",),
                ("instrument:eth",),
                None,
                "held_position",
            ),
        ),
    )

    checkpoints = build_checkpoints(reconciliation_states=(first, second))

    assert len(checkpoints) == 1
    assert checkpoints[0].reconciliation_state_refs == (
        "working/products/reconciliation_states/state-1/reconciliation_state.json",
        "working/products/reconciliation_states/state-2/reconciliation_state.json",
    )


def test_builder_skips_states_without_ready_proposals() -> None:
    state = _ready_state(proposal_status=CheckpointProposalStatus.BLOCKED)

    checkpoints = build_checkpoints(reconciliation_states=(state,))

    assert checkpoints == ()


def test_builder_maps_continuity_kind_from_segment_history() -> None:
    ready = _ready_state()
    observed_only = _ready_state(
        state_id="state-2",
        segment_start_at=datetime(2026, 3, 22, 23, 59, 59, tzinfo=UTC),
        segment_end_at=datetime(2026, 3, 22, 23, 59, 59, tzinfo=UTC),
    )

    checkpoints = build_checkpoints(reconciliation_states=(ready, observed_only))

    by_state = {
        assertion.checkpoint_id: tuple(
            item.continuity_kind for item in checkpoint.checkpoint_assertion_records
        )
        for checkpoint in checkpoints
        for assertion in checkpoint.checkpoint_assertion_records
    }
    assert (
        CheckpointAssertionContinuityKind.RECONCILED_ROLLFORWARD
        in by_state[checkpoints[0].checkpoint_id]
    )
    assert (
        CheckpointAssertionContinuityKind.OBSERVED_CONTINUITY
        in by_state[checkpoints[0].checkpoint_id]
    )


def _ready_state(
    *,
    state_id: str = "state-1",
    subject_ref: tuple[str, tuple[object, ...]] = (
        "position",
        (
            ("beneficial_owner:filing",),
            ("location:coinbase",),
            ("instrument:btc",),
            None,
            "held_position",
        ),
    ),
    segment_start_at: datetime | None = None,
    segment_end_at: datetime | None = None,
    proposal_status: CheckpointProposalStatus = CheckpointProposalStatus.READY,
) -> ReconciliationState:
    as_of = datetime(2026, 3, 22, 23, 59, 59, tzinfo=UTC)
    resolved_segment_start_at = segment_start_at or datetime(
        2024, 2, 8, 16, 31, 22, tzinfo=UTC
    )
    resolved_segment_end_at = segment_end_at or datetime(
        2026, 3, 22, 23, 59, 59, tzinfo=UTC
    )
    observed_value = QuantityValue(quantity=Decimal("1.25"), subject_ref=subject_ref)
    return ReconciliationState(
        reconciliation_state_id=state_id,
        economic_facts_ref="working/products/economic_facts/facts-1/economic_facts.json",
        continuity_segment_records=(
            ContinuitySegmentRecord(
                segment_id=f"segment-{state_id}",
                subject_ref=subject_ref,
                segment_start_at=resolved_segment_start_at,
                segment_end_at=resolved_segment_end_at,
                status=ContinuitySegmentStatus.COMPLETE,
                as_of=as_of,
            ),
        ),
        event_link_records=(),
        balance_target_records=(
            BalanceTargetRecord(
                target_id=f"target-{state_id}",
                segment_id=f"segment-{state_id}",
                subject_ref=subject_ref,
                kind=BalanceTargetKind.EXACT_BALANCE,
                as_of=as_of,
                expected_value=observed_value,
                observed_value=observed_value,
                observation_status=BalanceTargetObservationStatus.OBSERVED,
                comparison_outcome=ComparisonOutcome.MATCHED,
            ),
        ),
        checkpoint_proposal_records=(
            CheckpointProposalRecord(
                proposal_id=f"proposal-{state_id}",
                segment_id=f"segment-{state_id}",
                subject_ref=subject_ref,
                as_of=as_of,
                status=proposal_status,
                superseding_proposal_ref="",
                target_refs=(f"target-{state_id}",),
                evidence_refs=("statement.pdf#page=1",),
            ),
        ),
    )
