"""ClaimSet compatibility projection helpers."""

# pylint: disable=too-many-arguments

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from tallylot.adapters.support.drafts import economic_leg, symbol_claim
from tallylot.application.claim.contracts import DraftProjectionFieldRecord
from tallylot.domain.assessment import (
    GapExplanation,
    GapRecord,
    ReviewExplanation,
    ReviewRecord,
)
from tallylot.domain.claim import (
    ClaimKind,
    ClaimRecord,
    ClaimSet,
)
from tallylot.domain.evidence import EvidenceMemberKind, EvidenceSet
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.types import LocationId
from tallylot.domain.transactions import (
    AccountingIntentHint,
    EconomicKind,
    FactLegPolicy,
    LegKind,
    ProjectionHint,
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    TaxTreatmentHint,
    TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
)
from tallylot.ports.source_translation import (
    EconomicActivityDraft,
    SourceTranslationBatch,
    classification,
)


@dataclass(frozen=True)
class ClaimSetCompatibilityArtifacts:
    drafts: tuple[EconomicActivityDraft, ...]
    issues: tuple[IssueRecord, ...]
    reviews: tuple[NormalizationReviewRecord, ...]


def project_translation_batch_from_claim_set(
    *,
    claim_set: ClaimSet,
    evidence_set: EvidenceSet,
    draft_projection_field_records: tuple[DraftProjectionFieldRecord, ...],
    gap_records: tuple[GapRecord, ...],
    gap_explanations: tuple[GapExplanation, ...],
    review_records: tuple[ReviewRecord, ...],
    review_explanations: tuple[ReviewExplanation, ...],
) -> SourceTranslationBatch:
    artifacts = project_compatibility_artifacts_from_claim_set(
        claim_set=claim_set,
        evidence_set=evidence_set,
        draft_projection_field_records=draft_projection_field_records,
        gap_records=gap_records,
        gap_explanations=gap_explanations,
        review_records=review_records,
        review_explanations=review_explanations,
    )
    return SourceTranslationBatch(
        drafts=artifacts.drafts,
        balance_references=(),
        balance_reference_issues=(),
        issues=artifacts.issues,
        reviews=artifacts.reviews,
        location_inventory=(),
    )


def project_compatibility_artifacts_from_claim_set(
    *,
    claim_set: ClaimSet,
    evidence_set: EvidenceSet,
    draft_projection_field_records: tuple[DraftProjectionFieldRecord, ...],
    gap_records: tuple[GapRecord, ...],
    gap_explanations: tuple[GapExplanation, ...],
    review_records: tuple[ReviewRecord, ...],
    review_explanations: tuple[ReviewExplanation, ...],
) -> ClaimSetCompatibilityArtifacts:
    drafts = tuple(
        _draft_from_projection_record(
            claim_set=claim_set,
            evidence_set=evidence_set,
            record=record,
        )
        for record in sorted(
            draft_projection_field_records, key=lambda item: item.draft_order
        )
    )
    return ClaimSetCompatibilityArtifacts(
        drafts=drafts,
        issues=_issues_from_claim_assessment(
            evidence_set=evidence_set,
            gap_records=gap_records,
            gap_explanations=gap_explanations,
        ),
        reviews=_reviews_from_claim_assessment(
            evidence_set=evidence_set,
            review_records=review_records,
            review_explanations=review_explanations,
        ),
    )


def _draft_from_projection_record(
    *,
    claim_set: ClaimSet,
    evidence_set: EvidenceSet,
    record: DraftProjectionFieldRecord,
) -> EconomicActivityDraft:
    bundle_claims = [
        claim
        for claim in claim_set.claim_records
        if claim.bundle_id == record.claim_bundle_id
    ]
    activity_claim = next(
        claim for claim in bundle_claims if claim.kind is ClaimKind.ACTIVITY
    )
    location_claim = next(
        claim for claim in bundle_claims if claim.kind is ClaimKind.LOCATION
    )
    instrument_claim_by_id = {
        claim.claim_id: claim
        for claim in bundle_claims
        if claim.kind is ClaimKind.INSTRUMENT
    }
    raw_file = _raw_file_for_member_id(evidence_set, activity_claim.member_refs[0])
    raw_row_ref = activity_claim.key[1]
    legs = tuple(
        economic_leg(
            leg_id=spec.role,
            kind=LegKind.CHARGE if spec.role == "fee" else LegKind.PRIMARY,
            quantity=spec.quantity,
            instrument=symbol_claim(
                instrument_claim_by_id[spec.instrument_claim_refs[0]].value,
                venue=instrument_claim_by_id[spec.instrument_claim_refs[0]].venue,
            ),
            subtype=spec.subtype or None,
            attributed_to_leg_id=(
                None
                if spec.attributed_to_slot is None
                else activity_claim.leg_specs[spec.attributed_to_slot].role
            ),
        )
        for spec in activity_claim.leg_specs
    )
    return EconomicActivityDraft(
        activity_id=_activity_id(activity_claim.activity_label, raw_row_ref),
        source=_source_slug_from_claim_set_id(claim_set.claim_set_id),
        adapter_id="coinbase",
        timestamp=_activity_timestamp(activity_claim),
        location_id=LocationId(location_claim.location_ref),
        classification=classification(
            economic_kind=EconomicKind(record.economic_kind),
            projection_hint=(
                None
                if record.projection_hint == ""
                else ProjectionHint(record.projection_hint)
            ),
            accounting_intent_hint=AccountingIntentHint(record.accounting_intent_hint),
            tax_treatment_hint=TaxTreatmentHint(record.tax_treatment_hint),
        ),
        legs=legs,
        leg_policy=_leg_policy_for_activity(activity_claim.activity_label),
        description=record.description,
        raw_file=raw_file,
        raw_row_ref=raw_row_ref,
        tx_hash=record.tx_hash_or_null,
        provider_operation_key=_provider_operation_key(activity_claim.activity_label),
        operation_group_id=record.operation_group_id_or_null,
        provenance_refs=activity_claim.provenance_refs,
        confidence=record.confidence,
        status=record.status,
    )


def _issues_from_claim_assessment(
    *,
    evidence_set: EvidenceSet,
    gap_records: tuple[GapRecord, ...],
    gap_explanations: tuple[GapExplanation, ...],
) -> tuple[IssueRecord, ...]:
    explanation_by_gap_id = {item.gap_id: item for item in gap_explanations}
    issues: list[IssueRecord] = []
    for gap in gap_records:
        if gap.gap_key.startswith("unsupported_row:") is False:
            continue
        explanation = explanation_by_gap_id.get(gap.gap_id)
        member_id = (
            ""
            if explanation is None or not explanation.provenance_refs
            else explanation.provenance_refs[0]
        )
        raw_row_ref = gap.gap_key.split(":", 1)[1]
        issues.append(
            IssueRecord(
                issue_id=f"claim:{gap.gap_id}",
                source="coinbase",
                adapter_id="coinbase",
                severity="high",
                kind="unsupported_row",
                message=""
                if explanation is None or not explanation.known_facts
                else explanation.known_facts[0],
                raw_file=_raw_file_for_member_id(evidence_set, member_id),
                raw_row_ref=raw_row_ref,
            )
        )
    return tuple(issues)


def _reviews_from_claim_assessment(
    *,
    evidence_set: EvidenceSet,
    review_records: tuple[ReviewRecord, ...],
    review_explanations: tuple[ReviewExplanation, ...],
) -> tuple[NormalizationReviewRecord, ...]:
    explanation_by_review_id = {item.review_id: item for item in review_explanations}
    reviews: list[NormalizationReviewRecord] = []
    for review in review_records:
        explanation = explanation_by_review_id.get(review.review_id)
        member_id = (
            ""
            if explanation is None or not explanation.provenance_refs
            else explanation.provenance_refs[0]
        )
        reviews.append(
            NormalizationReviewRecord(
                review_id=review.review_id,
                source="coinbase",
                adapter_id="coinbase",
                scope="claim_scope",
                kind=review.review_kind,
                message="" if explanation is None else explanation.headline,
                raw_file=_raw_file_for_member_id(evidence_set, member_id),
                raw_row_ref=review.review_key.split(":", 1)[-1],
                field_name=(
                    ""
                    if ":" not in review.review_key
                    else review.review_key.split(":", 1)[0]
                ),
                original_value=(
                    ""
                    if explanation is None or not explanation.known_facts
                    else explanation.known_facts[0]
                ),
                normalized_value=(
                    ""
                    if explanation is None or len(explanation.known_facts) < 2
                    else explanation.known_facts[1]
                ),
            )
        )
    return tuple(reviews)


def _raw_file_for_member_id(evidence_set: EvidenceSet, member_id: str) -> str:
    for member in evidence_set.evidence_member_records:
        if (
            member.member_id == member_id
            and member.kind is EvidenceMemberKind.RETAIL_ACTIVITY_EXPORT_FILE
        ):
            return member.locator[0]
    return ""


def _source_slug_from_claim_set_id(claim_set_id: str) -> str:
    return claim_set_id.split(":", 1)[0]


def _provider_operation_key(activity_label: str) -> str:
    if activity_label == "reward_income":
        return "reward income"
    return activity_label


def _activity_id(activity_label: str, raw_row_ref: str) -> str:
    if activity_label == "asset_migration":
        sold_id, bought_id = raw_row_ref.split("|", 1)
        return f"coinbase-asset-migration-{sold_id}-{bought_id}"
    return f"coinbase-retail-{raw_row_ref}"


def _leg_policy_for_activity(activity_label: str) -> "FactLegPolicy":
    policy: FactLegPolicy
    if activity_label in {"buy", "sell"}:
        policy = TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY
    elif activity_label == "asset_migration":
        policy = TWO_SIDED_PRIMARY_EXCHANGE_POLICY
    else:
        policy = SINGLE_PRIMARY_ACTIVITY_POLICY
    return policy


def _activity_timestamp(activity_claim: ClaimRecord) -> datetime:
    if activity_claim.effective_at is None:
        raise ValueError(
            "activity claims must retain effective_at for compatibility projection"
        )
    return activity_claim.effective_at
