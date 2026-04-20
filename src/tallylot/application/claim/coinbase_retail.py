"""Retail-draft claim builders for Coinbase."""

from __future__ import annotations

from tallylot.application.claim.constants import FILING_BENEFICIAL_OWNER_REF
from tallylot.domain.claim import (
    ClaimKind,
    ClaimLegSpec,
    ClaimRecord,
    ClaimRecordStatus,
)
from tallylot.domain.claim.models import stable_claim_id
from tallylot.domain.instruments import InstrumentKind
from tallylot.domain.temporal import TemporalPrecision
from tallylot.ports.source_translation import EconomicActivityDraft, EconomicLegDraft


def claims_for_draft(
    *,
    claim_set_id: str,
    scope_id: str,
    bundle_id: str,
    scope_key: tuple[str, ...],
    draft: EconomicActivityDraft,
) -> tuple[ClaimRecord, ...]:
    location_claim_id = stable_claim_id(
        bundle_id=bundle_id,
        kind=ClaimKind.LOCATION,
        key=(*scope_key, ClaimKind.LOCATION.value, "0"),
    )
    beneficial_owner_claim_id = stable_claim_id(
        bundle_id=bundle_id,
        kind=ClaimKind.BENEFICIAL_OWNER,
        key=(*scope_key, ClaimKind.BENEFICIAL_OWNER.value, "0"),
    )
    instrument_claims: list[ClaimRecord] = []
    instrument_claim_ids_by_leg_id: dict[str, str] = {}
    instrument_claim_id_by_identity: dict[tuple[str, str, str, str, str], str] = {}
    for leg in draft.legs:
        identity = leg.instrument_identity_claims[0]
        instrument_kind = (
            identity.kind_hint.value
            if identity.kind_hint is not InstrumentKind.UNKNOWN
            else instrument_kind_for_symbol(identity.value).value
        )
        claim_name = identity.display_name or identity.value
        identity_key = (
            identity.scheme,
            identity.value,
            "" if identity.venue is None else identity.venue,
            instrument_kind,
            claim_name,
        )
        claim_id = instrument_claim_id_by_identity.get(identity_key)
        if claim_id is None:
            slot = str(len(instrument_claims))
            claim_id = stable_claim_id(
                bundle_id=bundle_id,
                kind=ClaimKind.INSTRUMENT,
                key=(*scope_key, ClaimKind.INSTRUMENT.value, slot),
            )
            instrument_claim_id_by_identity[identity_key] = claim_id
            instrument_claims.append(
                ClaimRecord(
                    claim_set_id=claim_set_id,
                    scope_id=scope_id,
                    bundle_id=bundle_id,
                    claim_id=claim_id,
                    kind=ClaimKind.INSTRUMENT,
                    status=ClaimRecordStatus.ASSERTED,
                    key=(*scope_key, ClaimKind.INSTRUMENT.value, slot),
                    member_refs=(scope_key[0],),
                    observation_refs=(),
                    effective_at=None,
                    precision=None,
                    provenance_refs=draft.provenance_refs,
                    scheme=identity.scheme,
                    value=identity.value,
                    venue="" if identity.venue is None else identity.venue,
                    instrument_kind=instrument_kind,
                    name=claim_name,
                )
            )
        instrument_claim_ids_by_leg_id[leg.leg_id] = claim_id
    activity_claim = ClaimRecord(
        claim_set_id=claim_set_id,
        scope_id=scope_id,
        bundle_id=bundle_id,
        claim_id=stable_claim_id(
            bundle_id=bundle_id,
            kind=ClaimKind.ACTIVITY,
            key=(*scope_key, ClaimKind.ACTIVITY.value, "0"),
        ),
        kind=ClaimKind.ACTIVITY,
        status=ClaimRecordStatus.ASSERTED,
        key=(*scope_key, ClaimKind.ACTIVITY.value, "0"),
        member_refs=(scope_key[0],),
        observation_refs=(),
        effective_at=draft.effective_at or draft.timestamp,
        precision=draft.effective_precision or TemporalPrecision.TIMESTAMP,
        provenance_refs=draft.provenance_refs,
        activity_label=activity_label(draft.provider_operation_key),
        location_claim_ref=location_claim_id,
        leg_specs=tuple(
            ClaimLegSpec(
                slot=index,
                role=leg.leg_id,
                quantity=leg.quantity,
                instrument_claim_refs=(instrument_claim_ids_by_leg_id[leg.leg_id],),
                location_claim_ref=location_claim_id,
                subtype="" if leg.subtype is None else leg.subtype,
                attributed_to_slot=attributed_slot(
                    leg.attributed_to_leg_id, draft.legs
                ),
            )
            for index, leg in enumerate(draft.legs)
        ),
    )
    return (
        activity_claim,
        ClaimRecord(
            claim_set_id=claim_set_id,
            scope_id=scope_id,
            bundle_id=bundle_id,
            claim_id=beneficial_owner_claim_id,
            kind=ClaimKind.BENEFICIAL_OWNER,
            status=ClaimRecordStatus.ASSERTED,
            key=(*scope_key, ClaimKind.BENEFICIAL_OWNER.value, "0"),
            member_refs=(scope_key[0],),
            observation_refs=(),
            effective_at=None,
            precision=None,
            provenance_refs=draft.provenance_refs,
            beneficial_owner_ref=FILING_BENEFICIAL_OWNER_REF,
        ),
        *instrument_claims,
        ClaimRecord(
            claim_set_id=claim_set_id,
            scope_id=scope_id,
            bundle_id=bundle_id,
            claim_id=location_claim_id,
            kind=ClaimKind.LOCATION,
            status=ClaimRecordStatus.ASSERTED,
            key=(*scope_key, ClaimKind.LOCATION.value, "0"),
            member_refs=(scope_key[0],),
            observation_refs=(),
            effective_at=None,
            precision=None,
            provenance_refs=draft.provenance_refs,
            location_ref=str(draft.location_id),
            location_group_label="Coinbase",
            location_label="Coinbase",
        ),
    )


def activity_label(provider_operation_key: str) -> str:
    return provider_operation_key.strip().lower().replace(" ", "_")


def instrument_kind_for_symbol(symbol: str) -> InstrumentKind:
    return (
        InstrumentKind.FIAT
        if symbol.strip().upper() in {"CAD", "USD"}
        else InstrumentKind.CRYPTO
    )


def attributed_slot(
    attributed_to_leg_id: str | None,
    legs: tuple[EconomicLegDraft, ...],
) -> int | None:
    if attributed_to_leg_id is None:
        return None
    index_by_leg_id = {leg.leg_id: index for index, leg in enumerate(legs)}
    return index_by_leg_id.get(attributed_to_leg_id)
