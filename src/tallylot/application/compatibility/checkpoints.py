"""Checkpoint compatibility projections."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath
from collections.abc import Mapping
from typing import cast

from tallylot.domain.assertion import QuantityValue
from tallylot.domain.balances import (
    BalanceReference,
    BalanceReferenceKind,
    BalanceTarget,
)
from tallylot.domain.checkpoint import Checkpoint
from tallylot.domain.evidence import EvidenceSet
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.reconciliation import ReconciliationState
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId


@dataclass(frozen=True)
class ObservationCompatibilityDetail:
    support_ref: str
    note: str = ""


def project_balance_references_from_checkpoint(
    *,
    checkpoint: Checkpoint,
    reconciliation_states: tuple[ReconciliationState, ...],
    observation_details: Mapping[str, ObservationCompatibilityDetail] | None = None,
) -> tuple[BalanceReference, ...]:
    states_by_id = {
        state.reconciliation_state_id: state for state in reconciliation_states
    }
    selected_states: list[ReconciliationState] = []
    for reconciliation_state_ref in checkpoint.reconciliation_state_refs:
        state = states_by_id.get(reconciliation_state_ref)
        if state is None:
            raise ValueError(
                "checkpoint compatibility requires referenced reconciliation state "
                f"{reconciliation_state_ref!r}"
            )
        selected_states.append(state)
    support_details = _support_details_by_subject(
        tuple(selected_states),
        observation_details=observation_details or {},
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
        detail = support_details.get((assertion.subject_ref, assertion.as_of))
        if detail is None:
            raise ValueError(
                "checkpoint compatibility requires support detail for "
                f"subject {assertion.subject_ref!r} at {assertion.as_of!s}"
            )
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
                support_ref=detail.support_ref,
                notes=detail.note,
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


def observation_details_from_evidence_set(
    evidence_set: EvidenceSet,
) -> dict[str, ObservationCompatibilityDetail]:
    member_path_by_id = {
        member.member_id: PurePath(member.locator[0]).name
        for member in evidence_set.evidence_member_records
        if member.locator
    }
    return {
        observation.observation_id: ObservationCompatibilityDetail(
            support_ref=member_path_by_id.get(observation.member_id, ""),
            note=observation.notes,
        )
        for observation in evidence_set.evidence_observation_records
        if member_path_by_id.get(observation.member_id, "")
    }


def _support_details_by_subject(
    reconciliation_states: tuple[ReconciliationState, ...],
    *,
    observation_details: Mapping[str, ObservationCompatibilityDetail],
) -> dict[tuple[object, object], ObservationCompatibilityDetail]:
    values: dict[tuple[object, object], ObservationCompatibilityDetail] = {}
    for state in reconciliation_states:
        targets_by_id = {
            target.target_id: target for target in state.balance_target_records
        }
        for proposal in state.checkpoint_proposal_records:
            if not proposal.target_refs or not proposal.evidence_refs:
                continue
            target = targets_by_id[proposal.target_refs[0]]
            values[(target.subject_ref, target.as_of)] = (
                _support_detail_for_evidence_refs(
                    proposal.evidence_refs,
                    observation_details=observation_details,
                )
            )
    return values


def _support_detail_for_evidence_refs(
    evidence_refs: tuple[str, ...],
    *,
    observation_details: Mapping[str, ObservationCompatibilityDetail],
) -> ObservationCompatibilityDetail:
    resolved_details = tuple(
        observation_details.get(ref, ObservationCompatibilityDetail(support_ref=ref))
        for ref in evidence_refs
    )
    noted_details = tuple(detail for detail in resolved_details if detail.note)
    if noted_details:
        return sorted(
            noted_details,
            key=lambda detail: (detail.support_ref, detail.note),
        )[0]
    anchored_details = tuple(
        detail for detail in resolved_details if "#" in detail.support_ref
    )
    if anchored_details:
        return sorted(
            anchored_details,
            key=lambda detail: (detail.support_ref, detail.note),
        )[0]
    return sorted(
        resolved_details,
        key=lambda detail: (detail.support_ref, detail.note),
    )[0]


def _subject_ref_text(subject_key: tuple[object, ...], index: int) -> str:
    value = subject_key[index]
    if not isinstance(value, tuple):
        raise ValueError("checkpoint compatibility requires position subject refs")
    tuple_value = cast(tuple[object, ...], value)
    if len(tuple_value) != 1 or not isinstance(tuple_value[0], str):
        raise ValueError("checkpoint compatibility requires position subject refs")
    return tuple_value[0]
