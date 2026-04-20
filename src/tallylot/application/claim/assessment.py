"""Claim-stage assessment mapping helpers."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.assessment import (
    GapConfidence,
    GapExplanation,
    GapKind,
    GapMateriality,
    GapRecord,
    GapStatus,
    ReviewConfidence,
    ReviewExplanation,
    ReviewRecord,
    ReviewStatus,
)
from tallylot.domain.claim import (
    ClaimBundleDecisionBasis,
    ClaimBundleDecisionOutcome,
    ClaimBundleDecisionRecord,
)
from tallylot.domain.claim.models import (
    stable_claim_bundle_decision_id,
    stable_claim_scope_id,
)
from tallylot.domain.assessment.models import stable_gap_id, stable_review_id
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord


@dataclass(frozen=True)
class ClaimIssueAssessment:
    scope_id: str
    bundle_decision: ClaimBundleDecisionRecord
    gap_record: GapRecord
    gap_explanation: GapExplanation
    compatibility_issue: IssueRecord


@dataclass(frozen=True)
class ClaimReviewAssessment:
    scope_id: str
    review_record: ReviewRecord
    review_explanation: ReviewExplanation
    compatibility_review: NormalizationReviewRecord


def map_claim_issue_to_scope(
    *,
    issue: IssueRecord,
    claim_set_id: str,
    retail_member_id: str,
) -> ClaimIssueAssessment | None:
    if issue.kind != "unsupported_row" or not issue.raw_row_ref:
        return None
    scope_id = stable_claim_scope_id(
        claim_set_id=claim_set_id,
        scope_key=(retail_member_id, issue.raw_row_ref),
    )
    gap_key = f"{issue.kind}:{issue.raw_row_ref}"
    gap_record = GapRecord(
        gap_id=stable_gap_id(
            owner_stage="claim",
            scope_kind="claim_scope",
            scope_ref=scope_id,
            gap_kind=GapKind.MANUAL_DECISION_REQUIRED,
            gap_key=gap_key,
        ),
        owner_stage="claim",
        blocking_stages=("claim", "economics"),
        scope_kind="claim_scope",
        scope_ref=scope_id,
        subject_ref=None,
        gap_kind=GapKind.MANUAL_DECISION_REQUIRED,
        gap_key=gap_key,
        status=GapStatus.OPEN,
        materiality=GapMateriality.MATERIAL,
        confidence=GapConfidence.HIGH,
    )
    return ClaimIssueAssessment(
        scope_id=scope_id,
        bundle_decision=ClaimBundleDecisionRecord(
            claim_set_id=claim_set_id,
            scope_id=scope_id,
            decision_id=stable_claim_bundle_decision_id(scope_id=scope_id),
            outcome=ClaimBundleDecisionOutcome.BLOCKED,
            accepted_bundle_ref="",
            rejected_bundle_refs=(),
            deferred_bundle_refs=(),
            basis=ClaimBundleDecisionBasis.UPSTREAM_GAP,
            blocking_gap_refs=(gap_record.gap_id,),
        ),
        gap_record=gap_record,
        gap_explanation=GapExplanation(
            gap_id=gap_record.gap_id,
            known_facts=(issue.message,),
            missing_inputs=(),
            possible_meanings=(),
            required_evidence=(),
            resolution_options=("model the unsupported retail row",),
            next_action="review the unsupported retail row before continuing claim emission",
            provenance_refs=(retail_member_id,),
        ),
        compatibility_issue=issue,
    )


def map_claim_review_to_scope(
    *,
    review: NormalizationReviewRecord,
    claim_set_id: str,
    retail_member_id: str,
) -> ClaimReviewAssessment | None:
    if not review.raw_row_ref:
        return None
    scope_id = stable_claim_scope_id(
        claim_set_id=claim_set_id,
        scope_key=(retail_member_id, review.raw_row_ref),
    )
    review_key = (
        f"{review.field_name}:{review.raw_row_ref}"
        if review.field_name
        else review.raw_row_ref
    )
    review_record = ReviewRecord(
        review_id=stable_review_id(
            owner_stage="claim",
            scope_kind="claim_scope",
            scope_ref=scope_id,
            review_kind=review.kind,
            review_key=review_key,
        ),
        owner_stage="claim",
        scope_kind="claim_scope",
        scope_ref=scope_id,
        subject_ref=None,
        review_kind=review.kind,
        review_key=review_key,
        status=ReviewStatus.OPEN,
        confidence=ReviewConfidence.MEDIUM,
        gap_ids=(),
    )
    return ClaimReviewAssessment(
        scope_id=scope_id,
        review_record=review_record,
        review_explanation=ReviewExplanation(
            review_id=review_record.review_id,
            headline=review.message,
            known_facts=tuple(
                value
                for value in (review.original_value, review.normalized_value)
                if value
            ),
            follow_up=("review the advisory normalization note during claim emission",),
            provenance_refs=(retail_member_id,),
        ),
        compatibility_review=review,
    )
