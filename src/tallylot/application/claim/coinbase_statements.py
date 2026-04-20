"""Statement-derived claim builders for Coinbase."""

from __future__ import annotations

from decimal import Decimal

from tallylot.application.claim.constants import FILING_BENEFICIAL_OWNER_REF
from tallylot.domain.claim import (
    ClaimBundleDecisionBasis,
    ClaimBundleDecisionOutcome,
    ClaimBundleDecisionRecord,
    ClaimBundleRecord,
    ClaimKind,
    ClaimRecord,
    ClaimRecordStatus,
)
from tallylot.domain.claim.models import (
    canonical_claim_bundle_decision_records,
    canonical_claim_bundle_records,
    canonical_claim_records,
    stable_claim_bundle_decision_id,
    stable_claim_bundle_id,
    stable_claim_id,
    stable_claim_scope_id,
)
from tallylot.domain.evidence import (
    EvidenceMemberKind,
    EvidenceMemberStatus,
    EvidenceObservationKind,
    EvidenceSet,
)
from tallylot.domain.location_identifiers import location_id_from_parts

from .coinbase_retail import instrument_kind_for_symbol


def statement_scope_claims(
    *,
    claim_set_id: str,
    evidence_set: EvidenceSet,
) -> tuple[
    tuple[ClaimRecord, ...],
    tuple[ClaimBundleRecord, ...],
    tuple[ClaimBundleDecisionRecord, ...],
]:
    claim_records: list[ClaimRecord] = []
    bundle_records: list[ClaimBundleRecord] = []
    decision_records: list[ClaimBundleDecisionRecord] = []
    document_observation_id_by_member_id = {
        observation.member_id: observation.observation_id
        for observation in evidence_set.evidence_observation_records
        if observation.kind is EvidenceObservationKind.STATEMENT_DOCUMENT
    }
    for member in evidence_set.evidence_member_records:
        if (
            member.kind is not EvidenceMemberKind.STATEMENT_DOCUMENT_FILE
            or member.status is not EvidenceMemberStatus.SELECTED
        ):
            continue
        row_observations = [
            observation
            for observation in evidence_set.evidence_observation_records
            if observation.member_id == member.member_id
            and observation.kind is EvidenceObservationKind.STATEMENT_BALANCE_ROW
        ]
        for observation in row_observations:
            row_key = observation.key[-1]
            scope_key = (member.member_id, row_key)
            scope_id = stable_claim_scope_id(
                claim_set_id=claim_set_id,
                scope_key=scope_key,
            )
            bundle_id = stable_claim_bundle_id(scope_id=scope_id, key="default")
            location_claim_id = stable_claim_id(
                bundle_id=bundle_id,
                kind=ClaimKind.LOCATION,
                key=(*scope_key, ClaimKind.LOCATION.value, "0"),
            )
            instrument_claim_id = stable_claim_id(
                bundle_id=bundle_id,
                kind=ClaimKind.INSTRUMENT,
                key=(*scope_key, ClaimKind.INSTRUMENT.value, "0"),
            )
            observation_refs = tuple(
                ref
                for ref in (
                    observation.observation_id,
                    document_observation_id_by_member_id.get(member.member_id, ""),
                )
                if ref
            )
            provenance_refs = observation_provenance_refs(observation.provenance_refs)
            claims = (
                ClaimRecord(
                    claim_set_id=claim_set_id,
                    scope_id=scope_id,
                    bundle_id=bundle_id,
                    claim_id=stable_claim_id(
                        bundle_id=bundle_id,
                        kind=ClaimKind.BALANCE,
                        key=(*scope_key, ClaimKind.BALANCE.value, "0"),
                    ),
                    kind=ClaimKind.BALANCE,
                    status=ClaimRecordStatus.ASSERTED,
                    key=(*scope_key, ClaimKind.BALANCE.value, "0"),
                    member_refs=(member.member_id,),
                    observation_refs=observation_refs,
                    effective_at=observation.observed_at,
                    precision=observation.precision,
                    provenance_refs=provenance_refs,
                    location_claim_ref=location_claim_id,
                    instrument_claim_refs=(instrument_claim_id,),
                    balance_kind=observation.balance_kind,
                    quantity=Decimal("0")
                    if observation.quantity is None
                    else observation.quantity,
                    observed_at=observation.observed_at,
                ),
                ClaimRecord(
                    claim_set_id=claim_set_id,
                    scope_id=scope_id,
                    bundle_id=bundle_id,
                    claim_id=stable_claim_id(
                        bundle_id=bundle_id,
                        kind=ClaimKind.BENEFICIAL_OWNER,
                        key=(*scope_key, ClaimKind.BENEFICIAL_OWNER.value, "0"),
                    ),
                    kind=ClaimKind.BENEFICIAL_OWNER,
                    status=ClaimRecordStatus.ASSERTED,
                    key=(*scope_key, ClaimKind.BENEFICIAL_OWNER.value, "0"),
                    member_refs=(member.member_id,),
                    observation_refs=observation_refs,
                    effective_at=None,
                    precision=None,
                    provenance_refs=provenance_refs,
                    beneficial_owner_ref=FILING_BENEFICIAL_OWNER_REF,
                ),
                ClaimRecord(
                    claim_set_id=claim_set_id,
                    scope_id=scope_id,
                    bundle_id=bundle_id,
                    claim_id=instrument_claim_id,
                    kind=ClaimKind.INSTRUMENT,
                    status=ClaimRecordStatus.ASSERTED,
                    key=(*scope_key, ClaimKind.INSTRUMENT.value, "0"),
                    member_refs=(member.member_id,),
                    observation_refs=observation_refs,
                    effective_at=None,
                    precision=None,
                    provenance_refs=provenance_refs,
                    scheme="symbol",
                    value=observation.instrument_symbol,
                    venue="coinbase",
                    instrument_kind=instrument_kind_for_symbol(
                        observation.instrument_symbol
                    ).value,
                    name=observation.instrument_symbol,
                ),
                ClaimRecord(
                    claim_set_id=claim_set_id,
                    scope_id=scope_id,
                    bundle_id=bundle_id,
                    claim_id=location_claim_id,
                    kind=ClaimKind.LOCATION,
                    status=ClaimRecordStatus.ASSERTED,
                    key=(*scope_key, ClaimKind.LOCATION.value, "0"),
                    member_refs=(member.member_id,),
                    observation_refs=observation_refs,
                    effective_at=None,
                    precision=None,
                    provenance_refs=provenance_refs,
                    location_ref=str(
                        _statement_location_ref(
                            source_slug=member.source_slug,
                            location_group_label=observation.location_group_label,
                            location_label=observation.location_label,
                        )
                    ),
                    location_group_label=observation.location_group_label,
                    location_label=observation.location_label,
                ),
            )
            claim_records.extend(claims)
            bundle_records.append(
                ClaimBundleRecord(
                    claim_set_id=claim_set_id,
                    scope_id=scope_id,
                    bundle_id=bundle_id,
                    key="default",
                    scope_key=scope_key,
                    claim_refs=tuple(claim.claim_id for claim in claims),
                )
            )
            decision_records.append(
                ClaimBundleDecisionRecord(
                    claim_set_id=claim_set_id,
                    scope_id=scope_id,
                    decision_id=stable_claim_bundle_decision_id(scope_id=scope_id),
                    outcome=ClaimBundleDecisionOutcome.ACCEPTED,
                    accepted_bundle_ref=bundle_id,
                    rejected_bundle_refs=(),
                    deferred_bundle_refs=(),
                    basis=ClaimBundleDecisionBasis.SINGLE_BUNDLE,
                    blocking_gap_refs=(),
                )
            )
    return (
        canonical_claim_records(tuple(claim_records)),
        canonical_claim_bundle_records(tuple(bundle_records)),
        canonical_claim_bundle_decision_records(tuple(decision_records)),
    )


def observation_provenance_refs(
    provenance_refs: tuple[tuple[str, ...], ...],
) -> tuple[str, ...]:
    return tuple(sorted(":".join(ref) for ref in provenance_refs))


def _statement_location_ref(
    *,
    source_slug: str,
    location_group_label: str,
    location_label: str,
) -> str:
    wallet_segment = location_label.strip()
    account_segment = location_group_label.strip()
    if wallet_segment and wallet_segment.casefold() != source_slug.strip().casefold():
        return str(location_id_from_parts(source_slug, wallet_segment))
    if account_segment and account_segment.casefold() != source_slug.strip().casefold():
        return str(location_id_from_parts(source_slug, account_segment))
    return str(location_id_from_parts(source_slug))
