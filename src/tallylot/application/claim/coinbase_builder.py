"""Coinbase ClaimSet builder."""

from __future__ import annotations

from tallylot.application.claim.assessment import (
    map_claim_issue_to_scope,
    map_claim_review_to_scope,
)
from tallylot.application.claim.coinbase_retail import claims_for_draft
from tallylot.application.claim.coinbase_statements import statement_scope_claims
from tallylot.application.claim.contracts import (
    CoinbaseClaimBuildResult,
    DraftProjectionFieldRecord,
)
from tallylot.domain.assessment import (
    GapExplanation,
    GapRecord,
    ReviewExplanation,
    ReviewRecord,
)
from tallylot.domain.claim import (
    ClaimBundleDecisionBasis,
    ClaimBundleDecisionOutcome,
    ClaimBundleDecisionRecord,
    ClaimBundleRecord,
    ClaimRecord,
    ClaimSet,
)
from tallylot.domain.claim.models import (
    canonical_claim_bundle_decision_records,
    canonical_claim_bundle_records,
    canonical_claim_records,
    stable_claim_bundle_decision_id,
    stable_claim_bundle_id,
    stable_claim_scope_id,
    stable_claim_set_id,
)
from tallylot.domain.evidence import (
    EvidenceMemberKind,
    EvidenceMemberRecord,
    EvidenceMemberStatus,
    EvidenceSet,
)
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.ports.source_profiles import SourceProfile
from tallylot.ports.source_translation import SourceTranslationBatch
from tallylot.application.normalization.translation_inputs.models import (
    TranslationInputPlanningResult,
)


def build_coinbase_claim_set(
    *,
    profile: SourceProfile,
    evidence_set: EvidenceSet | None,
    evidence_set_ref: str,
    planning_result: TranslationInputPlanningResult,
    batch: SourceTranslationBatch,
) -> CoinbaseClaimBuildResult | None:
    if (
        evidence_set is None
        or planning_result.plan.blocked
        or not _selected_retail_members(evidence_set)
    ):
        return None
    emitter_id = f"{profile.source}:{profile.adapter_id}:claim"
    claim_set_id = stable_claim_set_id(
        evidence_set_id=evidence_set.evidence_set_id,
        emitter_id=emitter_id,
    )
    claim_records: list[ClaimRecord] = []
    bundle_records: list[ClaimBundleRecord] = []
    decision_records: list[ClaimBundleDecisionRecord] = []
    gap_records: list[GapRecord] = []
    gap_explanations: list[GapExplanation] = []
    review_records: list[ReviewRecord] = []
    review_explanations: list[ReviewExplanation] = []
    compatibility_issues: list[IssueRecord] = []
    compatibility_reviews: list[NormalizationReviewRecord] = []
    projection_fields: list[DraftProjectionFieldRecord] = []

    retail_member_ids = _selected_retail_members(evidence_set)
    retail_member_id_by_file = {
        member.locator[0]: member.member_id for member in retail_member_ids
    }
    for draft_order, draft in enumerate(batch.drafts):
        retail_member_id = retail_member_id_by_file.get(draft.raw_file)
        if retail_member_id is None:
            continue
        scope_key = (retail_member_id, draft.raw_row_ref)
        scope_id = stable_claim_scope_id(claim_set_id=claim_set_id, scope_key=scope_key)
        bundle_id = stable_claim_bundle_id(scope_id=scope_id, key="default")
        claims = claims_for_draft(
            claim_set_id=claim_set_id,
            scope_id=scope_id,
            bundle_id=bundle_id,
            scope_key=scope_key,
            draft=draft,
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
        projection_fields.append(
            DraftProjectionFieldRecord(
                claim_bundle_id=bundle_id,
                economic_kind=draft.classification.economic_kind.value,
                projection_hint=(
                    ""
                    if draft.classification.projection_hint is None
                    else draft.classification.projection_hint.value
                ),
                accounting_intent_hint=draft.classification.accounting_intent_hint.value,
                tax_treatment_hint=draft.classification.tax_treatment_hint.value,
                description=draft.description,
                tx_hash_or_null=draft.tx_hash,
                operation_group_id_or_null=draft.operation_group_id,
                confidence=draft.confidence,
                status=draft.status,
                draft_order=draft_order,
            )
        )
    statement_claims, statement_bundles, statement_decisions = statement_scope_claims(
        claim_set_id=claim_set_id,
        evidence_set=evidence_set,
    )
    claim_records.extend(statement_claims)
    bundle_records.extend(statement_bundles)
    decision_records.extend(statement_decisions)

    for issue in batch.issues:
        mapping = map_claim_issue_to_scope(
            issue=issue,
            claim_set_id=claim_set_id,
            retail_member_id=retail_member_id_by_file.get(issue.raw_file, ""),
        )
        if mapping is None:
            continue
        decision_records.append(mapping.bundle_decision)
        gap_records.append(mapping.gap_record)
        gap_explanations.append(mapping.gap_explanation)
        compatibility_issues.append(mapping.compatibility_issue)
    for review in batch.reviews:
        review_mapping = map_claim_review_to_scope(
            review=review,
            claim_set_id=claim_set_id,
            retail_member_id=retail_member_id_by_file.get(review.raw_file, ""),
        )
        if review_mapping is None:
            continue
        review_records.append(review_mapping.review_record)
        review_explanations.append(review_mapping.review_explanation)
        compatibility_reviews.append(review_mapping.compatibility_review)

    claim_set = ClaimSet(
        claim_set_id=claim_set_id,
        evidence_set_ref=evidence_set_ref,
        emitter_id=emitter_id,
        claim_records=canonical_claim_records(tuple(claim_records)),
        claim_bundle_records=canonical_claim_bundle_records(tuple(bundle_records)),
        claim_bundle_decision_records=canonical_claim_bundle_decision_records(
            tuple(decision_records)
        ),
    )
    return CoinbaseClaimBuildResult(
        claim_set=claim_set,
        gap_records=tuple(gap_records),
        gap_explanations=tuple(gap_explanations),
        review_records=tuple(review_records),
        review_explanations=tuple(review_explanations),
        draft_projection_field_records=tuple(
            sorted(projection_fields, key=lambda item: item.draft_order)
        ),
        compatibility_issue_records=tuple(compatibility_issues),
        compatibility_review_records=tuple(compatibility_reviews),
    )


def _selected_retail_members(
    evidence_set: EvidenceSet,
) -> tuple[EvidenceMemberRecord, ...]:
    return tuple(
        member
        for member in evidence_set.evidence_member_records
        if member.kind is EvidenceMemberKind.RETAIL_ACTIVITY_EXPORT_FILE
        and member.status is EvidenceMemberStatus.SELECTED
    )
