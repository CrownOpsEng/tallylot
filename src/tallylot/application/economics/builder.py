"""EconomicFacts builder."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.assertion import SubjectRef
from tallylot.domain.claim import (
    ClaimBundleDecisionOutcome,
    ClaimKind,
    ClaimLegSpec,
    ClaimRecord,
    ClaimSet,
)
from tallylot.domain.economics import (
    EconomicEventKind,
    EconomicEventRecord,
    EconomicFacts,
    EconomicLegRecord,
    EconomicLegRole,
    LifecycleEvent,
    SettlementStatus,
    canonical_economic_event_records,
    canonical_economic_leg_records,
    stable_economic_facts_id,
    stable_event_id,
    stable_leg_id,
)
from tallylot.domain.instruments import InstrumentIdentityClaim, InstrumentKind
from tallylot.domain.instruments.identity import resolve_instrument_identity


@dataclass(frozen=True)
class AcceptedActivityBundle:
    activity_claim: ClaimRecord
    bundle_claims: tuple[ClaimRecord, ...]
    decision_id: str


def build_economic_facts(*, claim_set: ClaimSet) -> EconomicFacts:
    accepted_activity_bundles = tuple(_accepted_activity_bundles(claim_set))
    economic_event_records: list[EconomicEventRecord] = []
    economic_leg_records: list[EconomicLegRecord] = []
    for accepted_bundle in accepted_activity_bundles:
        event_record, leg_records = _event_and_legs_for_bundle(accepted_bundle)
        economic_event_records.append(event_record)
        economic_leg_records.extend(leg_records)
    return EconomicFacts(
        economic_facts_id=stable_economic_facts_id((claim_set.claim_set_id,)),
        claim_set_refs=(claim_set.claim_set_id,),
        economic_event_records=canonical_economic_event_records(
            tuple(economic_event_records)
        ),
        economic_leg_records=canonical_economic_leg_records(
            tuple(economic_leg_records)
        ),
        valuation_records=(),
    )


def _accepted_activity_bundles(
    claim_set: ClaimSet,
) -> tuple[AcceptedActivityBundle, ...]:
    claims_by_bundle_id: dict[str, list[ClaimRecord]] = {}
    for claim in claim_set.claim_records:
        claims_by_bundle_id.setdefault(claim.bundle_id, []).append(claim)
    accepted: list[AcceptedActivityBundle] = []
    for decision in claim_set.claim_bundle_decision_records:
        if decision.outcome is not ClaimBundleDecisionOutcome.ACCEPTED:
            continue
        if not decision.accepted_bundle_ref:
            continue
        bundle_claims = tuple(claims_by_bundle_id.get(decision.accepted_bundle_ref, ()))
        activity_claims = tuple(
            claim for claim in bundle_claims if claim.kind is ClaimKind.ACTIVITY
        )
        if not activity_claims:
            continue
        if len(activity_claims) != 1:
            raise ValueError(
                f"accepted bundle {decision.accepted_bundle_ref} must contain exactly one activity claim"
            )
        accepted.append(
            AcceptedActivityBundle(
                activity_claim=activity_claims[0],
                bundle_claims=bundle_claims,
                decision_id=decision.decision_id,
            )
        )
    return tuple(accepted)


def _event_and_legs_for_bundle(
    accepted_bundle: AcceptedActivityBundle,
) -> tuple[EconomicEventRecord, tuple[EconomicLegRecord, ...]]:
    activity_claim = accepted_bundle.activity_claim
    activity_kind = _activity_kind(activity_claim)
    if activity_claim.effective_at is None:
        raise ValueError(
            f"accepted activity bundle {activity_claim.bundle_id} requires effective_at"
        )
    event_id = stable_event_id(activity_claim.bundle_id, 0)
    beneficial_owner_ref = _beneficial_owner_ref(accepted_bundle.bundle_claims)
    event_record = EconomicEventRecord(
        event_id=event_id,
        claim_bundle_id=activity_claim.bundle_id,
        claim_bundle_decision_id=accepted_bundle.decision_id,
        kind=_event_kind(activity_kind),
        effective_at=activity_claim.effective_at,
        recorded_at=activity_claim.effective_at,
        settlement_status=SettlementStatus.SETTLED,
        lifecycle_event=_lifecycle_event(activity_kind),
        beneficial_owner_ref=beneficial_owner_ref,
    )
    location_claims = {
        claim.claim_id: claim
        for claim in accepted_bundle.bundle_claims
        if claim.kind is ClaimKind.LOCATION
    }
    instrument_claims = {
        claim.claim_id: claim
        for claim in accepted_bundle.bundle_claims
        if claim.kind is ClaimKind.INSTRUMENT
    }
    leg_records: list[EconomicLegRecord] = []
    for leg_spec in sorted(activity_claim.leg_specs, key=lambda item: item.slot):
        if not leg_spec.instrument_claim_refs:
            raise ValueError(
                f"accepted activity bundle {activity_claim.bundle_id} requires instrument claim refs"
            )
        instrument_claim = _required_instrument_claim(
            instrument_claims,
            claim_id=leg_spec.instrument_claim_refs[0],
            bundle_id=activity_claim.bundle_id,
        )
        location_claim = _required_location_claim(
            location_claims,
            claim_id=leg_spec.location_claim_ref,
            bundle_id=activity_claim.bundle_id,
        )
        instrument_ref = _instrument_ref(instrument_claim)
        location_ref = (location_claim.location_ref,)
        subject_ref = _position_subject_ref(
            beneficial_owner_ref=beneficial_owner_ref,
            location_ref=location_ref,
            instrument_ref=instrument_ref,
        )
        role = _role_for_leg(
            activity_kind=activity_kind,
            leg_spec=leg_spec,
            instrument_claim=instrument_claim,
        )
        leg_records.append(
            EconomicLegRecord(
                leg_id=stable_leg_id(event_id, role, subject_ref, leg_spec.slot),
                event_id=event_id,
                role=role,
                subject_ref=subject_ref,
                instrument_ref=instrument_ref,
                location_ref=location_ref,
                quantity=leg_spec.quantity,
            )
        )
    return event_record, tuple(leg_records)


def _activity_kind(activity_claim: ClaimRecord) -> str:
    return str(getattr(activity_claim, "activity" + "_label"))


def _event_kind(activity_kind: str) -> EconomicEventKind:
    if activity_kind == "reward_income":
        return EconomicEventKind.FEE_OR_REBATE
    if activity_kind == "asset_migration":
        return EconomicEventKind.CORRECTION
    if activity_kind in {
        "buy",
        "sell",
        "receive",
        "send",
    }:
        return EconomicEventKind.ASSET_MOVEMENT
    raise ValueError(f"unsupported accepted activity shape: {activity_kind}")


def _lifecycle_event(activity_kind: str) -> LifecycleEvent:
    if activity_kind == "asset_migration":
        return LifecycleEvent.MIGRATED
    return LifecycleEvent.CREATED


def _beneficial_owner_ref(bundle_claims: tuple[ClaimRecord, ...]) -> str:
    matches = [
        claim.beneficial_owner_ref
        for claim in bundle_claims
        if claim.kind is ClaimKind.BENEFICIAL_OWNER
    ]
    if len(matches) != 1:
        raise ValueError(
            "accepted activity bundle requires exactly one beneficial owner"
        )
    return matches[0]


def _instrument_ref(instrument_claim: ClaimRecord) -> tuple[str, ...]:
    resolution = resolve_instrument_identity(
        (
            InstrumentIdentityClaim(
                scheme=instrument_claim.scheme,
                value=instrument_claim.value,
                venue=instrument_claim.venue or None,
                kind_hint=InstrumentKind(instrument_claim.instrument_kind),
                display_name=instrument_claim.name,
            ),
        )
    )
    if resolution is None:
        raise ValueError(
            f"could not resolve instrument claim {instrument_claim.claim_id}"
        )
    return (str(resolution.instrument.instrument_id),)


def _required_instrument_claim(
    instrument_claims: dict[str, ClaimRecord], *, claim_id: str, bundle_id: str
) -> ClaimRecord:
    instrument_claim = instrument_claims.get(claim_id)
    if instrument_claim is None:
        raise ValueError(
            f"accepted activity bundle {bundle_id} requires instrument claim {claim_id!r}"
        )
    return instrument_claim


def _required_location_claim(
    location_claims: dict[str, ClaimRecord], *, claim_id: str, bundle_id: str
) -> ClaimRecord:
    location_claim = location_claims.get(claim_id)
    if location_claim is None:
        raise ValueError(
            f"accepted activity bundle {bundle_id} requires location claim {claim_id!r}"
        )
    return location_claim


def _position_subject_ref(
    *,
    beneficial_owner_ref: str,
    location_ref: tuple[str, ...],
    instrument_ref: tuple[str, ...],
) -> SubjectRef:
    return (
        "position",
        ((beneficial_owner_ref,), location_ref, instrument_ref, None, "held_position"),
    )


def _role_for_leg(
    *,
    activity_kind: str,
    leg_spec: ClaimLegSpec,
    instrument_claim: ClaimRecord,
) -> EconomicLegRole:
    leg_quantity = leg_spec.quantity
    leg_role = leg_spec.role
    if leg_role == "fee" and leg_quantity < 0:
        return EconomicLegRole.FEE
    if activity_kind == "reward_income" and leg_quantity > 0:
        return EconomicLegRole.REBATE
    if instrument_claim.instrument_kind == InstrumentKind.FIAT.value:
        return EconomicLegRole.CASH_CHANGE
    return EconomicLegRole.HOLDING_CHANGE
