from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from tallylot.domain.assertion import QuantityValue
from tallylot.domain.balances import BalanceSnapshot
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

from tallylot.application.compatibility.reconciliation_states import (
    project_balance_snapshots_from_reconciliation_state,
)


def test_reconciliation_projection_preserves_balance_snapshot_shape() -> None:
    subject_ref = (
        "position",
        (
            ("beneficial_owner:filing",),
            ("location:coinbase",),
            ("instrument:btc",),
            None,
            "held_position",
        ),
    )
    as_of = datetime(2026, 3, 22, 23, 59, 59, tzinfo=UTC)
    quantity = QuantityValue(quantity=Decimal("1.25"), subject_ref=subject_ref)
    state = ReconciliationState(
        reconciliation_state_id="state-1",
        economic_facts_ref="facts-1",
        continuity_segment_records=(
            ContinuitySegmentRecord(
                segment_id="segment-1",
                subject_ref=subject_ref,
                segment_start_at=datetime(2024, 2, 8, 16, 31, 22, tzinfo=UTC),
                segment_end_at=as_of,
                status=ContinuitySegmentStatus.COMPLETE,
                as_of=as_of,
            ),
        ),
        event_link_records=(),
        balance_target_records=(
            BalanceTargetRecord(
                target_id="target-1",
                segment_id="segment-1",
                subject_ref=subject_ref,
                kind=BalanceTargetKind.EXACT_BALANCE,
                as_of=as_of,
                expected_value=quantity,
                observed_value=quantity,
                observation_status=BalanceTargetObservationStatus.OBSERVED,
                comparison_outcome=ComparisonOutcome.MATCHED,
            ),
        ),
        checkpoint_proposal_records=(
            CheckpointProposalRecord(
                proposal_id="proposal-1",
                segment_id="segment-1",
                subject_ref=subject_ref,
                as_of=as_of,
                status=CheckpointProposalStatus.READY,
                superseding_proposal_ref="",
                target_refs=("target-1",),
                evidence_refs=("observation:document",),
            ),
        ),
    )

    snapshots = project_balance_snapshots_from_reconciliation_state(state)

    assert snapshots == (
        BalanceSnapshot(
            target=snapshots[0].target,
            quantity=Decimal("1.25"),
            snapshot_basis="fact_cutoff",
        ),
    )
