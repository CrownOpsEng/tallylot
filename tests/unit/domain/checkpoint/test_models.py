from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from tallylot.domain.assertion import QuantityValue
from tallylot.domain.checkpoint import (
    CHECKPOINT_SCHEMA_VERSION,
    Checkpoint,
    CheckpointAssertionBasis,
    CheckpointAssertionContinuityKind,
    CheckpointAssertionRecord,
    CheckpointAssertionSupportShape,
    CheckpointAssertionTrustLevel,
    CheckpointAssertionValueKind,
    CheckpointRecord,
    canonical_checkpoint_assertion_records,
    checkpoint_fingerprint,
    stable_checkpoint_assertion_id,
    stable_checkpoint_id,
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


def test_checkpoint_payload_shape_and_fingerprint_are_stable() -> None:
    subject_ref = _subject_ref()
    as_of = datetime(2026, 3, 22, 23, 59, 59, tzinfo=UTC)
    accepted_value = QuantityValue(quantity=Decimal("1.25"), subject_ref=subject_ref)
    checkpoint_id = stable_checkpoint_id(
        reconciliation_state_refs=(
            "working/products/reconciliation_states/state-1/reconciliation_state.json",
        ),
        as_of=as_of,
    )
    checkpoint = Checkpoint(
        checkpoint_id=checkpoint_id,
        reconciliation_state_refs=(
            "working/products/reconciliation_states/state-1/reconciliation_state.json",
        ),
        as_of=as_of,
        checkpoint_records=(
            CheckpointRecord(
                checkpoint_id=checkpoint_id,
                as_of=as_of,
                assertion_ids=(
                    stable_checkpoint_assertion_id(
                        kind=CheckpointAssertionValueKind.POSITION_QUANTITY,
                        as_of=as_of,
                        subject_ref=subject_ref,
                        accepted_value=accepted_value,
                    ),
                ),
                proposal_refs=("proposal-1",),
            ),
        ),
        checkpoint_assertion_records=(
            CheckpointAssertionRecord(
                assertion_id=stable_checkpoint_assertion_id(
                    kind=CheckpointAssertionValueKind.POSITION_QUANTITY,
                    as_of=as_of,
                    subject_ref=subject_ref,
                    accepted_value=accepted_value,
                ),
                checkpoint_id=checkpoint_id,
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

    payload = checkpoint.to_payload()

    assert payload["schema_version"] == CHECKPOINT_SCHEMA_VERSION
    assert checkpoint_fingerprint(checkpoint) == checkpoint_fingerprint(checkpoint)


def test_checkpoint_assertion_ordering_is_canonical() -> None:
    subject_ref = _subject_ref()
    earlier = datetime(2026, 3, 21, 23, 59, 59, tzinfo=UTC)
    later = datetime(2026, 3, 22, 23, 59, 59, tzinfo=UTC)
    earlier_value = QuantityValue(quantity=Decimal("1.00"), subject_ref=subject_ref)
    later_value = QuantityValue(quantity=Decimal("1.25"), subject_ref=subject_ref)
    later_assertion = CheckpointAssertionRecord(
        assertion_id=stable_checkpoint_assertion_id(
            kind=CheckpointAssertionValueKind.POSITION_QUANTITY,
            as_of=later,
            subject_ref=subject_ref,
            accepted_value=later_value,
        ),
        checkpoint_id="checkpoint-1",
        subject_ref=subject_ref,
        kind=CheckpointAssertionValueKind.POSITION_QUANTITY,
        as_of=later,
        accepted_value=later_value,
        trust_level=CheckpointAssertionTrustLevel.FILING_READY,
        basis=CheckpointAssertionBasis.DOCUMENT_SUPPORT,
        support_shape=CheckpointAssertionSupportShape.DOCUMENT_OBSERVATION,
        continuity_kind=CheckpointAssertionContinuityKind.RECONCILED_ROLLFORWARD,
    )
    earlier_assertion = CheckpointAssertionRecord(
        assertion_id=stable_checkpoint_assertion_id(
            kind=CheckpointAssertionValueKind.POSITION_QUANTITY,
            as_of=earlier,
            subject_ref=subject_ref,
            accepted_value=earlier_value,
        ),
        checkpoint_id="checkpoint-0",
        subject_ref=subject_ref,
        kind=CheckpointAssertionValueKind.POSITION_QUANTITY,
        as_of=earlier,
        accepted_value=earlier_value,
        trust_level=CheckpointAssertionTrustLevel.FILING_READY,
        basis=CheckpointAssertionBasis.DOCUMENT_SUPPORT,
        support_shape=CheckpointAssertionSupportShape.DOCUMENT_OBSERVATION,
        continuity_kind=CheckpointAssertionContinuityKind.OBSERVED_CONTINUITY,
    )

    assert canonical_checkpoint_assertion_records(
        (later_assertion, earlier_assertion)
    ) == (earlier_assertion, later_assertion)


def test_checkpoint_product_id_is_path_safe_and_stable() -> None:
    checkpoint_id = stable_checkpoint_id(
        reconciliation_state_refs=(
            "working/products/reconciliation_states/state-1/reconciliation_state.json",
            "working/products/reconciliation_states/state-2/reconciliation_state.json",
        ),
        as_of=datetime(2026, 3, 22, 23, 59, 59, tzinfo=UTC),
    )

    assert checkpoint_id == stable_checkpoint_id(
        reconciliation_state_refs=(
            "working/products/reconciliation_states/state-2/reconciliation_state.json",
            "working/products/reconciliation_states/state-1/reconciliation_state.json",
        ),
        as_of=datetime(2026, 3, 22, 23, 59, 59, tzinfo=UTC),
    )
    assert len(checkpoint_id) == 64
    assert "/" not in checkpoint_id
