"""EconomicFacts compatibility projections."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import PurePath
from typing import cast

from tallylot.application.claim.contracts import DraftProjectionFieldRecord
from tallylot.application.normalization.annotations import FactAnnotationRecord
from tallylot.domain.claim import ClaimKind, ClaimRecord, ClaimSet
from tallylot.domain.economics import EconomicFacts, EconomicLegRecord, EconomicLegRole
from tallylot.domain.evidence import EvidenceMemberKind, EvidenceSet
from tallylot.domain.transactions import (
    AccountingIntentHint,
    EconomicKind,
    EconomicLeg,
    FactLegPolicy,
    FactSemantics,
    LegKind,
    ProjectionHint,
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
    TaxTreatmentHint,
    TransactionFact,
)
from tallylot.domain.types import AdapterId, LocationId, SourceId, TransactionId
from tallylot.domain.instruments import InstrumentId


@dataclass(frozen=True)
class EconomicFactsCompatibilityArtifacts:
    facts: tuple[TransactionFact, ...]
    fact_annotations: tuple[FactAnnotationRecord, ...]


def project_compatibility_artifacts_from_economic_facts(
    *,
    economic_facts: EconomicFacts,
    claim_set: ClaimSet,
    evidence_set: EvidenceSet,
    draft_projection_field_records: tuple[DraftProjectionFieldRecord, ...],
) -> EconomicFactsCompatibilityArtifacts:
    if claim_set.claim_set_id not in economic_facts.claim_set_refs:
        raise ValueError(
            "economic facts compatibility requires matching claim_set lineage"
        )
    records_by_bundle_id = {
        record.claim_bundle_id: record for record in draft_projection_field_records
    }
    facts: list[TransactionFact] = []
    annotations: list[FactAnnotationRecord] = []
    claims_by_bundle_id: dict[str, list[ClaimRecord]] = {}
    for claim in claim_set.claim_records:
        claims_by_bundle_id.setdefault(claim.bundle_id, []).append(claim)
    legs_by_event_id: dict[str, list[EconomicLegRecord]] = {}
    for leg_record in economic_facts.economic_leg_records:
        legs_by_event_id.setdefault(leg_record.event_id, []).append(leg_record)
    ordered_events = sorted(
        economic_facts.economic_event_records,
        key=lambda record: _projection_fields_for_bundle(
            records_by_bundle_id,
            claim_bundle_id=record.claim_bundle_id,
        ).draft_order,
    )
    for event_record in ordered_events:
        bundle_claims = tuple(claims_by_bundle_id.get(event_record.claim_bundle_id, ()))
        if not bundle_claims:
            raise ValueError(
                "economic facts compatibility requires claim bundle "
                f"{event_record.claim_bundle_id!r}"
            )
        activity_claim = _require_bundle_claim(
            bundle_claims,
            claim_bundle_id=event_record.claim_bundle_id,
            kind=ClaimKind.ACTIVITY,
        )
        location_claim = _require_bundle_claim(
            bundle_claims,
            claim_bundle_id=event_record.claim_bundle_id,
            kind=ClaimKind.LOCATION,
        )
        projection_fields = _projection_fields_for_bundle(
            records_by_bundle_id,
            claim_bundle_id=event_record.claim_bundle_id,
        )
        instrument_claims = {
            claim.claim_id: claim
            for claim in bundle_claims
            if claim.kind is ClaimKind.INSTRUMENT
        }
        fact_id = _activity_id(activity_claim.activity_label, activity_claim.key[1])
        legs = tuple(
            _compatibility_leg(
                leg_record=leg_record,
                activity_claim=activity_claim,
                instrument_claims=instrument_claims,
            )
            for leg_record in sorted(
                legs_by_event_id.get(event_record.event_id, ()),
                key=lambda item: _leg_slot_from_id(item.leg_id),
            )
        )
        facts.append(
            TransactionFact(
                fact_id=TransactionId(fact_id),
                source=SourceId(
                    _source_slug_for_member_id(
                        evidence_set, activity_claim.member_refs[0]
                    )
                ),
                adapter_id=AdapterId("coinbase"),
                timestamp=event_record.effective_at,
                effective_at=event_record.effective_at,
                effective_precision=activity_claim.precision,
                location_id=LocationId(location_claim.location_ref),
                semantics=FactSemantics(
                    economic_kind=EconomicKind(projection_fields.economic_kind),
                    accounting_intent_hint=AccountingIntentHint(
                        projection_fields.accounting_intent_hint
                    ),
                    tax_treatment_hint=TaxTreatmentHint(
                        projection_fields.tax_treatment_hint
                    ),
                    projection_hint=(
                        None
                        if projection_fields.projection_hint == ""
                        else ProjectionHint(projection_fields.projection_hint)
                    ),
                ),
                legs=legs,
                leg_policy=_leg_policy_for_activity(activity_claim.activity_label),
                description=projection_fields.description,
                provider_operation_key=_provider_operation_key(
                    activity_claim.activity_label
                ),
                operation_group_id=projection_fields.operation_group_id_or_null,
                tx_hash=projection_fields.tx_hash_or_null or None,
                raw_file=_raw_file_for_member_id(
                    evidence_set, activity_claim.member_refs[0]
                ),
                raw_row_ref=activity_claim.key[1],
                confidence=projection_fields.confidence,
                status=projection_fields.status,
            )
        )
        annotations.append(
            FactAnnotationRecord(
                fact_id=fact_id,
                provenance_refs=activity_claim.provenance_refs,
                review_markers=(),
                adapter_metadata=(),
            )
        )
    return EconomicFactsCompatibilityArtifacts(
        facts=tuple(facts),
        fact_annotations=tuple(annotations),
    )


def _compatibility_leg(
    *,
    leg_record: object,
    activity_claim: ClaimRecord,
    instrument_claims: dict[str, ClaimRecord],
) -> EconomicLeg:
    leg_slot = _leg_slot_from_id(getattr(leg_record, "leg_id"))
    if leg_slot >= len(activity_claim.leg_specs):
        raise ValueError(
            "economic facts compatibility leg slot "
            f"{leg_slot} exceeds activity leg spec count"
        )
    matching_spec = activity_claim.leg_specs[leg_slot]
    if not matching_spec.instrument_claim_refs:
        raise ValueError("economic facts compatibility requires instrument claim refs")
    instrument_claim = instrument_claims.get(matching_spec.instrument_claim_refs[0])
    if instrument_claim is None:
        raise ValueError(
            "economic facts compatibility could not resolve instrument claim "
            f"{matching_spec.instrument_claim_refs[0]!r}"
        )
    role = getattr(leg_record, "role")
    return EconomicLeg(
        leg_id=matching_spec.role,
        kind=_leg_kind(role),
        instrument_id=InstrumentId(
            instrument_claim.value
            if instrument_claim.venue == ""
            else f"{instrument_claim.scheme}:{instrument_claim.value}@{instrument_claim.venue}"
        ),
        quantity=getattr(leg_record, "quantity"),
        subtype=matching_spec.subtype or None,
        attributed_to_leg_id=(
            None
            if matching_spec.attributed_to_slot is None
            else activity_claim.leg_specs[matching_spec.attributed_to_slot].role
        ),
    )


def _leg_slot_from_id(leg_id: str) -> int:
    payload = cast(list[object], json.loads(leg_id))
    if len(payload) != 4 or not isinstance(payload[3], int):
        raise ValueError(f"invalid compatibility leg_id: {leg_id}")
    return payload[3]


def _leg_kind(role: EconomicLegRole) -> LegKind:
    if role is EconomicLegRole.FEE:
        return LegKind.CHARGE
    if role is EconomicLegRole.REBATE:
        return LegKind.PRIMARY
    return LegKind.PRIMARY


def _provider_operation_key(activity_label: str) -> str:
    if activity_label == "reward_income":
        return "reward income"
    return activity_label


def _projection_fields_for_bundle(
    records_by_bundle_id: dict[str, DraftProjectionFieldRecord],
    *,
    claim_bundle_id: str,
) -> DraftProjectionFieldRecord:
    projection_fields = records_by_bundle_id.get(claim_bundle_id)
    if projection_fields is None:
        raise ValueError(
            "economic facts compatibility requires draft projection fields for "
            f"claim bundle {claim_bundle_id!r}"
        )
    return projection_fields


def _require_bundle_claim(
    bundle_claims: tuple[ClaimRecord, ...],
    *,
    claim_bundle_id: str,
    kind: ClaimKind,
) -> ClaimRecord:
    for claim in bundle_claims:
        if claim.kind is kind:
            return claim
    raise ValueError(
        "economic facts compatibility requires "
        f"{kind.value!r} claim in bundle {claim_bundle_id!r}"
    )


def _activity_id(activity_label: str, raw_row_ref: str) -> str:
    if activity_label == "asset_migration":
        sold_id, bought_id = raw_row_ref.split("|", 1)
        return f"coinbase-asset-migration-{sold_id}-{bought_id}"
    return f"coinbase-retail-{raw_row_ref}"


def _leg_policy_for_activity(activity_label: str) -> FactLegPolicy:
    if activity_label in {"buy", "sell"}:
        return TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY
    if activity_label == "asset_migration":
        return TWO_SIDED_PRIMARY_EXCHANGE_POLICY
    return SINGLE_PRIMARY_ACTIVITY_POLICY


def _raw_file_for_member_id(evidence_set: EvidenceSet, member_id: str) -> str:
    for member in evidence_set.evidence_member_records:
        if member.member_id == member_id:
            return PurePath(member.locator[0]).name
    raise ValueError(f"could not resolve member_id {member_id!r}")


def _source_slug_for_member_id(evidence_set: EvidenceSet, member_id: str) -> str:
    for member in evidence_set.evidence_member_records:
        if (
            member.member_id == member_id
            and member.kind is EvidenceMemberKind.RETAIL_ACTIVITY_EXPORT_FILE
        ):
            return member.source_slug
    raise ValueError(f"could not resolve member_id {member_id!r}")
