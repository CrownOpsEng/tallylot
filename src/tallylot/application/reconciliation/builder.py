"""ReconciliationState builder."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

from tallylot.domain.assertion import QuantityValue, SubjectRef
from tallylot.domain.claim import ClaimKind, ClaimRecord, ClaimSet
from tallylot.domain.economics import EconomicFacts, EconomicLegRecord
from tallylot.domain.evidence import EvidenceSet
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
    canonical_balance_target_records,
    canonical_checkpoint_proposal_records,
    stable_balance_target_id,
    stable_checkpoint_proposal_id,
    stable_continuity_segment_id,
    stable_reconciliation_state_id,
)


class TimedEconomicLeg(NamedTuple):
    record: EconomicLegRecord
    effective_at: datetime


def build_reconciliation_states(
    *,
    economic_facts: EconomicFacts,
    claim_set: ClaimSet,
    evidence_set: EvidenceSet,
) -> tuple[ReconciliationState, ...]:
    del evidence_set
    event_times = {
        event.event_id: event.effective_at
        for event in economic_facts.economic_event_records
    }
    legs_by_subject: dict[SubjectRef, list[TimedEconomicLeg]] = defaultdict(list)
    for leg in economic_facts.economic_leg_records:
        effective_at = event_times.get(leg.event_id)
        if effective_at is None:
            raise ValueError(f"economic leg {leg.leg_id} references unknown event_id")
        legs_by_subject[leg.subject_ref].append(TimedEconomicLeg(leg, effective_at))
    balance_claims_by_subject: dict[SubjectRef, list[ClaimRecord]] = defaultdict(list)
    for claim in claim_set.claim_records:
        if claim.kind is not ClaimKind.BALANCE:
            continue
        subject_ref = _subject_ref_for_balance_claim(claim_set, claim)
        balance_claims_by_subject[subject_ref].append(claim)
    states: list[ReconciliationState] = []
    all_subjects = tuple(
        sorted(set(legs_by_subject) | set(balance_claims_by_subject), key=str)
    )
    for subject_ref in all_subjects:
        legs = tuple(legs_by_subject.get(subject_ref, ()))
        balance_claims = tuple(balance_claims_by_subject.get(subject_ref, ()))
        if not legs and not balance_claims:
            continue
        state = _state_for_subject(
            subject_ref=subject_ref,
            economic_facts_ref=(
                f"working/products/economic_facts/{economic_facts.economic_facts_id}/economic_facts.json"
            ),
            legs=legs,
            balance_claims=balance_claims,
        )
        states.append(state)
    return tuple(states)


def _state_for_subject(
    *,
    subject_ref: SubjectRef,
    economic_facts_ref: str,
    legs: tuple[TimedEconomicLeg, ...],
    balance_claims: tuple[ClaimRecord, ...],
) -> ReconciliationState:
    segment_start_at, segment_end_at = _segment_bounds(legs, balance_claims)
    segment_id = stable_continuity_segment_id(
        subject_ref=subject_ref,
        segment_start_at=segment_start_at,
        segment_end_at=segment_end_at,
    )
    segment_status = (
        ContinuitySegmentStatus.COMPLETE
        if balance_claims
        else ContinuitySegmentStatus.PARTIAL
    )
    target_records: list[BalanceTargetRecord] = []
    proposal_records: list[CheckpointProposalRecord] = []
    for claim in sorted(
        balance_claims, key=lambda item: item.observed_at or segment_end_at
    ):
        as_of = claim.observed_at or segment_end_at
        expected_quantity = _expected_quantity(legs, as_of=as_of)
        expected_value = QuantityValue(
            quantity=expected_quantity, subject_ref=subject_ref
        )
        observed_value = (
            None
            if claim.quantity is None
            else QuantityValue(quantity=claim.quantity, subject_ref=subject_ref)
        )
        observation_status = (
            BalanceTargetObservationStatus.OBSERVED
            if observed_value is not None
            else BalanceTargetObservationStatus.UNOBSERVED
        )
        comparison_outcome = (
            None
            if observed_value is None
            else (
                ComparisonOutcome.MATCHED
                if observed_value == expected_value
                else ComparisonOutcome.MISMATCHED
            )
        )
        target_id = stable_balance_target_id(
            segment_id=segment_id,
            subject_ref=subject_ref,
            kind=BalanceTargetKind.EXACT_BALANCE,
            as_of=as_of,
            expected_value=expected_value,
        )
        target_record = BalanceTargetRecord(
            target_id=target_id,
            segment_id=segment_id,
            subject_ref=subject_ref,
            kind=BalanceTargetKind.EXACT_BALANCE,
            as_of=as_of,
            expected_value=expected_value,
            observed_value=observed_value,
            observation_status=observation_status,
            comparison_outcome=comparison_outcome,
        )
        target_records.append(target_record)
        proposal_records.append(
            CheckpointProposalRecord(
                proposal_id=stable_checkpoint_proposal_id(
                    segment_id=segment_id,
                    subject_ref=subject_ref,
                    as_of=as_of,
                    target_refs=(target_id,),
                ),
                segment_id=segment_id,
                subject_ref=subject_ref,
                as_of=as_of,
                status=_proposal_status(target_record, claim),
                superseding_proposal_ref="",
                target_refs=(target_id,),
                evidence_refs=tuple(sorted(claim.observation_refs)),
            )
        )
    state_id = stable_reconciliation_state_id(
        economic_facts_ref=economic_facts_ref,
        segment_id=segment_id,
    )
    as_of = max(
        [segment_end_at, *[record.as_of for record in target_records]],
    )
    return ReconciliationState(
        reconciliation_state_id=state_id,
        economic_facts_ref=economic_facts_ref,
        continuity_segment_records=(
            ContinuitySegmentRecord(
                segment_id=segment_id,
                subject_ref=subject_ref,
                segment_start_at=segment_start_at,
                segment_end_at=segment_end_at,
                status=segment_status,
                as_of=as_of,
            ),
        ),
        event_link_records=(),
        balance_target_records=canonical_balance_target_records(tuple(target_records)),
        checkpoint_proposal_records=canonical_checkpoint_proposal_records(
            tuple(proposal_records)
        ),
    )


def _segment_bounds(
    legs: tuple[TimedEconomicLeg, ...], balance_claims: tuple[ClaimRecord, ...]
) -> tuple[datetime, datetime]:
    times_real: list[datetime] = []
    for leg in legs:
        times_real.append(leg.effective_at)
    for claim in balance_claims:
        if claim.observed_at is not None:
            times_real.append(claim.observed_at)
    if not times_real:
        raise ValueError("reconciliation subject requires at least one bounded time")
    return min(times_real), max(times_real)


def _expected_quantity(
    legs: tuple[TimedEconomicLeg, ...], *, as_of: datetime
) -> Decimal:
    quantity = Decimal("0")
    for leg in legs:
        if leg.effective_at > as_of:
            continue
        quantity += leg.record.quantity
    return quantity


def _proposal_status(
    target_record: BalanceTargetRecord, claim: ClaimRecord
) -> CheckpointProposalStatus:
    if target_record.observation_status is not BalanceTargetObservationStatus.OBSERVED:
        return CheckpointProposalStatus.PARTIAL
    if target_record.comparison_outcome is ComparisonOutcome.MATCHED:
        return (
            CheckpointProposalStatus.READY
            if claim.observation_refs
            else CheckpointProposalStatus.PARTIAL
        )
    return CheckpointProposalStatus.BLOCKED


def _subject_ref_for_balance_claim(
    claim_set: ClaimSet, claim: ClaimRecord
) -> SubjectRef:
    bundle_claims = tuple(
        item for item in claim_set.claim_records if item.bundle_id == claim.bundle_id
    )
    beneficial_owner_ref = next(
        item.beneficial_owner_ref
        for item in bundle_claims
        if item.kind is ClaimKind.BENEFICIAL_OWNER
    )
    location_claim = next(
        item for item in bundle_claims if item.claim_id == claim.location_claim_ref
    )
    instrument_claim = next(
        item
        for item in bundle_claims
        if item.claim_id == claim.instrument_claim_refs[0]
    )
    return (
        "position",
        (
            (beneficial_owner_ref,),
            (location_claim.location_ref,),
            (f"instrument:{instrument_claim.value.lower()}",),
            None,
            "held_position",
        ),
    )
