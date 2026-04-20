"""Checkpoint compatibility projections."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from tallylot.domain.assertion import QuantityValue
from tallylot.domain.balances import (
    BalanceReference,
    BalanceReferenceKind,
    BalanceTarget,
)
from tallylot.domain.checkpoint import Checkpoint
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.reconciliation import ReconciliationState
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId


def project_balance_references_from_checkpoint(
    *,
    checkpoint: Checkpoint,
    reconciliation_states: tuple[ReconciliationState, ...],
    observation_support_refs: Mapping[str, str] | None = None,
) -> tuple[BalanceReference, ...]:
    support_refs = _support_refs_by_subject(
        reconciliation_states,
        observation_support_refs=observation_support_refs or {},
    )
    references: list[BalanceReference] = []
    for assertion in checkpoint.checkpoint_assertion_records:
        accepted_value = assertion.accepted_value
        if not isinstance(accepted_value, QuantityValue):
            raise ValueError(
                "checkpoint compatibility requires QuantityValue assertions"
            )
        subject_key = assertion.subject_ref[1]
        location_ref = _subject_ref_text(subject_key, 1)
        instrument_ref = _subject_ref_text(subject_key, 2)
        references.append(
            BalanceReference(
                target=BalanceTarget(
                    source=SourceId("coinbase"),
                    location_id=LocationId(location_ref),
                    instrument_id=InstrumentId(instrument_ref),
                    balance_kind="available",
                    target_at=assertion.as_of,
                    target_precision=TemporalPrecision.TIMESTAMP,
                ),
                quantity=accepted_value.quantity,
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
                observed_at=assertion.as_of,
                observed_precision=TemporalPrecision.TIMESTAMP,
                support_ref=support_refs[(assertion.subject_ref, assertion.as_of)],
            )
        )
    return tuple(
        sorted(
            references,
            key=lambda item: (
                str(item.target.source),
                str(item.target.location_id),
                str(item.target.instrument_id),
                item.target.balance_kind,
                item.target.target_at,
                item.support_ref,
            ),
        )
    )


def _support_refs_by_subject(
    reconciliation_states: tuple[ReconciliationState, ...],
    *,
    observation_support_refs: Mapping[str, str],
) -> dict[tuple[object, object], str]:
    values: dict[tuple[object, object], str] = {}
    for state in reconciliation_states:
        targets_by_id = {
            target.target_id: target for target in state.balance_target_records
        }
        for proposal in state.checkpoint_proposal_records:
            if not proposal.target_refs or not proposal.evidence_refs:
                continue
            target = targets_by_id[proposal.target_refs[0]]
            values[(target.subject_ref, target.as_of)] = _support_ref_for_evidence_refs(
                proposal.evidence_refs,
                observation_support_refs=observation_support_refs,
            )
    return values


def _support_ref_for_evidence_refs(
    evidence_refs: tuple[str, ...],
    *,
    observation_support_refs: Mapping[str, str],
) -> str:
    resolved_support_refs = tuple(
        observation_support_refs.get(ref, ref) for ref in evidence_refs
    )
    anchored_refs = tuple(ref for ref in resolved_support_refs if "#" in ref)
    if anchored_refs:
        return sorted(anchored_refs)[0]
    return sorted(resolved_support_refs)[0]


def _subject_ref_text(subject_key: tuple[object, ...], index: int) -> str:
    value = subject_key[index]
    if not isinstance(value, tuple):
        raise ValueError("checkpoint compatibility requires position subject refs")
    tuple_value = cast(tuple[object, ...], value)
    if len(tuple_value) != 1 or not isinstance(tuple_value[0], str):
        raise ValueError("checkpoint compatibility requires position subject refs")
    return tuple_value[0]
