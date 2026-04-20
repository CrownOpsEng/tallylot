from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from tallylot.domain.assertion import QuantityValue
from tallylot.domain.balances import BalanceReference, BalanceReferenceKind
from tallylot.domain.checkpoint import (
    Checkpoint,
    CheckpointAssertionBasis,
    CheckpointAssertionContinuityKind,
    CheckpointAssertionRecord,
    CheckpointAssertionSupportShape,
    CheckpointAssertionTrustLevel,
    CheckpointAssertionValueKind,
    CheckpointRecord,
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

from tallylot.application.compatibility.checkpoints import (
    ObservationCompatibilityDetail,
    project_balance_references_from_checkpoint,
)


def test_checkpoint_projection_preserves_balance_reference_shape() -> None:
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
    accepted_value = QuantityValue(quantity=Decimal("1.25"), subject_ref=subject_ref)
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
                expected_value=accepted_value,
                observed_value=accepted_value,
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
                evidence_refs=("statement.pdf#page=1",),
            ),
        ),
    )
    checkpoint = Checkpoint(
        checkpoint_id="checkpoint-1",
        reconciliation_state_refs=("state-1",),
        as_of=as_of,
        checkpoint_records=(
            CheckpointRecord(
                checkpoint_id="checkpoint-1",
                as_of=as_of,
                assertion_ids=("assertion-1",),
                proposal_refs=("proposal-1",),
            ),
        ),
        checkpoint_assertion_records=(
            CheckpointAssertionRecord(
                assertion_id="assertion-1",
                checkpoint_id="checkpoint-1",
                subject_ref=subject_ref,
                kind=CheckpointAssertionValueKind.POSITION_QUANTITY,
                as_of=as_of,
                accepted_value=accepted_value,
                trust_level=CheckpointAssertionTrustLevel.FILING_READY,
                basis=CheckpointAssertionBasis.DOCUMENT_SUPPORT,
                support_shape=CheckpointAssertionSupportShape.DOCUMENT_OBSERVATION,
                continuity_kind=CheckpointAssertionContinuityKind.RECONCILED_ROLLFORWARD,
            ),
        ),
    )

    references = project_balance_references_from_checkpoint(
        checkpoint=checkpoint,
        reconciliation_states=(state,),
    )

    assert references == (
        BalanceReference(
            target=references[0].target,
            quantity=Decimal("1.25"),
            reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
            observed_at=as_of,
            observed_precision=references[0].observed_precision,
            support_ref="statement.pdf#page=1",
        ),
    )


def test_checkpoint_projection_resolves_observation_ids_to_support_refs() -> None:
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
    accepted_value = QuantityValue(quantity=Decimal("1.25"), subject_ref=subject_ref)
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
                expected_value=accepted_value,
                observed_value=accepted_value,
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
                evidence_refs=("observation-document", "observation-row"),
            ),
        ),
    )
    checkpoint = Checkpoint(
        checkpoint_id="checkpoint-1",
        reconciliation_state_refs=("state-1",),
        as_of=as_of,
        checkpoint_records=(
            CheckpointRecord(
                checkpoint_id="checkpoint-1",
                as_of=as_of,
                assertion_ids=("assertion-1",),
                proposal_refs=("proposal-1",),
            ),
        ),
        checkpoint_assertion_records=(
            CheckpointAssertionRecord(
                assertion_id="assertion-1",
                checkpoint_id="checkpoint-1",
                subject_ref=subject_ref,
                kind=CheckpointAssertionValueKind.POSITION_QUANTITY,
                as_of=as_of,
                accepted_value=accepted_value,
                trust_level=CheckpointAssertionTrustLevel.FILING_READY,
                basis=CheckpointAssertionBasis.DOCUMENT_SUPPORT,
                support_shape=CheckpointAssertionSupportShape.DOCUMENT_OBSERVATION,
                continuity_kind=CheckpointAssertionContinuityKind.RECONCILED_ROLLFORWARD,
            ),
        ),
    )

    references = project_balance_references_from_checkpoint(
        checkpoint=checkpoint,
        reconciliation_states=(state,),
        observation_details={
            "observation-document": ObservationCompatibilityDetail(
                support_ref="statement.pdf"
            ),
            "observation-row": ObservationCompatibilityDetail(
                support_ref="statement.pdf#page=1",
                note="Portfolio summary asset balance from Coinbase statement PDF",
            ),
        },
    )

    assert references[0].support_ref == "statement.pdf#page=1"
    assert (
        references[0].notes
        == "Portfolio summary asset balance from Coinbase statement PDF"
    )
