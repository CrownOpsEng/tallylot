"""Checkpoint builder."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import NamedTuple

from tallylot.domain.assertion import QuantityValue
from tallylot.domain.checkpoint import (
    Checkpoint,
    CheckpointAssertionBasis,
    CheckpointAssertionContinuityKind,
    CheckpointAssertionRecord,
    CheckpointAssertionSupportShape,
    CheckpointAssertionTrustLevel,
    CheckpointAssertionValueKind,
    CheckpointRecord,
    canonical_checkpoint_assertion_records,
    stable_checkpoint_assertion_id,
    stable_checkpoint_id,
)
from tallylot.domain.reconciliation import (
    BalanceTargetRecord,
    BalanceTargetObservationStatus,
    CheckpointProposalStatus,
    CheckpointProposalRecord,
    ComparisonOutcome,
    ContinuitySegmentRecord,
    ReconciliationState,
)


class ReadyCheckpointRow(NamedTuple):
    state: ReconciliationState
    proposal: CheckpointProposalRecord
    segment: ContinuitySegmentRecord
    target: BalanceTargetRecord


def build_checkpoints(
    *, reconciliation_states: tuple[ReconciliationState, ...]
) -> tuple[Checkpoint, ...]:
    ready_rows_by_as_of: dict[datetime, list[ReadyCheckpointRow]] = defaultdict(list)
    for state in reconciliation_states:
        targets_by_id = {
            target.target_id: target for target in state.balance_target_records
        }
        segment = state.continuity_segment_records[0]
        for proposal in state.checkpoint_proposal_records:
            if proposal.status is not CheckpointProposalStatus.READY:
                continue
            target = targets_by_id[proposal.target_refs[0]]
            ready_rows_by_as_of[proposal.as_of].append(
                ReadyCheckpointRow(state, proposal, segment, target)
            )
    checkpoints: list[Checkpoint] = []
    for as_of, rows in sorted(ready_rows_by_as_of.items()):
        reconciliation_state_refs = tuple(
            sorted(
                f"working/products/reconciliation_states/{state.reconciliation_state_id}/reconciliation_state.json"
                for state, _proposal, _segment, _target in rows
            )
        )
        checkpoint_id = stable_checkpoint_id(
            reconciliation_state_refs=reconciliation_state_refs,
            as_of=as_of,
        )
        assertions: list[CheckpointAssertionRecord] = []
        proposal_refs: list[str] = []
        for _state, proposal, segment, target in rows:
            if not isinstance(target.observed_value, QuantityValue):
                raise ValueError(
                    "ready checkpoint proposals require observed QuantityValue"
                )
            if target.observation_status is not BalanceTargetObservationStatus.OBSERVED:
                raise ValueError(
                    "ready checkpoint proposals require observed balance targets"
                )
            if target.comparison_outcome is not ComparisonOutcome.MATCHED:
                raise ValueError(
                    "ready checkpoint proposals require matched balance targets"
                )
            proposal_refs.append(proposal.proposal_id)
            assertions.append(
                CheckpointAssertionRecord(
                    assertion_id=stable_checkpoint_assertion_id(
                        kind=CheckpointAssertionValueKind.POSITION_QUANTITY,
                        as_of=as_of,
                        subject_ref=target.subject_ref,
                        accepted_value=target.observed_value,
                    ),
                    checkpoint_id=checkpoint_id,
                    subject_ref=target.subject_ref,
                    kind=CheckpointAssertionValueKind.POSITION_QUANTITY,
                    as_of=as_of,
                    accepted_value=target.observed_value,
                    trust_level=CheckpointAssertionTrustLevel.FILING_READY,
                    basis=CheckpointAssertionBasis.DOCUMENT_SUPPORT,
                    support_shape=CheckpointAssertionSupportShape.DOCUMENT_OBSERVATION,
                    continuity_kind=_continuity_kind(segment.segment_start_at, as_of),
                )
            )
        ordered_assertions = canonical_checkpoint_assertion_records(tuple(assertions))
        checkpoints.append(
            Checkpoint(
                checkpoint_id=checkpoint_id,
                reconciliation_state_refs=reconciliation_state_refs,
                as_of=as_of,
                checkpoint_records=(
                    CheckpointRecord(
                        checkpoint_id=checkpoint_id,
                        as_of=as_of,
                        assertion_ids=tuple(
                            record.assertion_id for record in ordered_assertions
                        ),
                        proposal_refs=tuple(sorted(proposal_refs)),
                    ),
                ),
                checkpoint_assertion_records=ordered_assertions,
            )
        )
    return tuple(checkpoints)


def _continuity_kind(
    segment_start_at: datetime, as_of: datetime
) -> CheckpointAssertionContinuityKind:
    if segment_start_at < as_of:
        return CheckpointAssertionContinuityKind.RECONCILED_ROLLFORWARD
    return CheckpointAssertionContinuityKind.OBSERVED_CONTINUITY
