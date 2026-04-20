from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from tallylot.domain.assertion import QuantityValue
from tallylot.domain.reconciliation import (
    RECONCILIATION_STATE_SCHEMA_VERSION,
    BalanceTargetKind,
    BalanceTargetRecord,
    BalanceTargetObservationStatus,
    CheckpointProposalRecord,
    CheckpointProposalStatus,
    ComparisonOutcome,
    ContinuitySegmentRecord,
    ContinuitySegmentStatus,
    ReconciliationState,
    canonical_balance_target_records,
    canonical_checkpoint_proposal_records,
    reconciliation_state_fingerprint,
    stable_balance_target_id,
    stable_checkpoint_proposal_id,
    stable_continuity_segment_id,
    stable_reconciliation_state_id,
)


def _subject_ref() -> tuple[str, tuple[object, ...]]:
    return (
        "position",
        (
            ("beneficial_owner:filing",),
            ("location:coinbase",),
            ("instrument:btc",),
            None,
            "held_position",
        ),
    )


def test_reconciliation_state_payload_shape_and_fingerprint_are_stable() -> None:
    subject_ref = _subject_ref()
    as_of = datetime(2026, 3, 22, 23, 59, 59, tzinfo=UTC)
    expected_value = QuantityValue(quantity=Decimal("1.25"), subject_ref=subject_ref)
    observed_value = QuantityValue(quantity=Decimal("1.25"), subject_ref=subject_ref)
    segment_id = stable_continuity_segment_id(
        subject_ref=subject_ref,
        segment_start_at=datetime(2024, 2, 8, 16, 31, 22, tzinfo=UTC),
        segment_end_at=as_of,
    )
    target_id = stable_balance_target_id(
        segment_id=segment_id,
        subject_ref=subject_ref,
        kind=BalanceTargetKind.EXACT_BALANCE,
        as_of=as_of,
        expected_value=expected_value,
    )
    proposal_id = stable_checkpoint_proposal_id(
        segment_id=segment_id,
        subject_ref=subject_ref,
        as_of=as_of,
        target_refs=(target_id,),
    )
    state = ReconciliationState(
        reconciliation_state_id=stable_reconciliation_state_id(
            economic_facts_ref="working/products/economic_facts/facts-1/economic_facts.json",
            segment_id=segment_id,
        ),
        economic_facts_ref="working/products/economic_facts/facts-1/economic_facts.json",
        continuity_segment_records=(
            ContinuitySegmentRecord(
                segment_id=segment_id,
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
                target_id=target_id,
                segment_id=segment_id,
                subject_ref=subject_ref,
                kind=BalanceTargetKind.EXACT_BALANCE,
                as_of=as_of,
                expected_value=expected_value,
                observed_value=observed_value,
                observation_status=BalanceTargetObservationStatus.OBSERVED,
                comparison_outcome=ComparisonOutcome.MATCHED,
            ),
        ),
        checkpoint_proposal_records=(
            CheckpointProposalRecord(
                proposal_id=proposal_id,
                segment_id=segment_id,
                subject_ref=subject_ref,
                as_of=as_of,
                status=CheckpointProposalStatus.READY,
                superseding_proposal_ref="",
                target_refs=(target_id,),
                evidence_refs=("observation:document", "observation:row"),
            ),
        ),
    )

    payload = state.to_payload()

    assert payload["schema_version"] == RECONCILIATION_STATE_SCHEMA_VERSION
    assert payload["event_link_records"] == []
    assert reconciliation_state_fingerprint(state) == reconciliation_state_fingerprint(
        state
    )


def test_reconciliation_state_ordering_is_canonical() -> None:
    subject_ref = _subject_ref()
    later = datetime(2026, 3, 23, tzinfo=UTC)
    earlier = datetime(2026, 3, 22, tzinfo=UTC)
    value = QuantityValue(quantity=Decimal("1"), subject_ref=subject_ref)
    segment_id = stable_continuity_segment_id(
        subject_ref=subject_ref,
        segment_start_at=earlier,
        segment_end_at=later,
    )
    second_target = BalanceTargetRecord(
        target_id=stable_balance_target_id(
            segment_id=segment_id,
            subject_ref=subject_ref,
            kind=BalanceTargetKind.EXACT_BALANCE,
            as_of=later,
            expected_value=value,
        ),
        segment_id=segment_id,
        subject_ref=subject_ref,
        kind=BalanceTargetKind.EXACT_BALANCE,
        as_of=later,
        expected_value=value,
        observed_value=value,
        observation_status=BalanceTargetObservationStatus.OBSERVED,
        comparison_outcome=ComparisonOutcome.MATCHED,
    )
    first_target = BalanceTargetRecord(
        target_id=stable_balance_target_id(
            segment_id=segment_id,
            subject_ref=subject_ref,
            kind=BalanceTargetKind.EXACT_BALANCE,
            as_of=earlier,
            expected_value=value,
        ),
        segment_id=segment_id,
        subject_ref=subject_ref,
        kind=BalanceTargetKind.EXACT_BALANCE,
        as_of=earlier,
        expected_value=value,
        observed_value=value,
        observation_status=BalanceTargetObservationStatus.OBSERVED,
        comparison_outcome=ComparisonOutcome.MATCHED,
    )
    second_proposal = CheckpointProposalRecord(
        proposal_id=stable_checkpoint_proposal_id(
            segment_id=segment_id,
            subject_ref=subject_ref,
            as_of=later,
            target_refs=(second_target.target_id,),
        ),
        segment_id=segment_id,
        subject_ref=subject_ref,
        as_of=later,
        status=CheckpointProposalStatus.BLOCKED,
        superseding_proposal_ref="",
        target_refs=(second_target.target_id,),
        evidence_refs=("z", "a"),
    )
    first_proposal = CheckpointProposalRecord(
        proposal_id=stable_checkpoint_proposal_id(
            segment_id=segment_id,
            subject_ref=subject_ref,
            as_of=earlier,
            target_refs=(first_target.target_id,),
        ),
        segment_id=segment_id,
        subject_ref=subject_ref,
        as_of=earlier,
        status=CheckpointProposalStatus.PARTIAL,
        superseding_proposal_ref="",
        target_refs=(first_target.target_id,),
        evidence_refs=("row",),
    )

    assert canonical_balance_target_records((second_target, first_target)) == (
        first_target,
        second_target,
    )
    assert canonical_checkpoint_proposal_records((second_proposal, first_proposal)) == (
        first_proposal,
        second_proposal,
    )
