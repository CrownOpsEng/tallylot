from __future__ import annotations

import pytest

from tallylot.domain.assessment import (
    ASSESSMENT_SCHEMA_VERSION,
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
from tallylot.domain.assessment.models import (
    canonical_gap_records,
    canonical_review_records,
    gap_explanations_payload,
    gap_records_payload,
    review_explanations_payload,
    review_records_payload,
    stable_gap_id,
    stable_review_id,
)


def test_assessment_models_use_declared_field_sets_and_stable_ids() -> None:
    gap = GapRecord(
        gap_id=stable_gap_id(
            owner_stage="claim",
            scope_kind="claim_scope",
            scope_ref="scope-1",
            gap_kind=GapKind.MISSING_EVIDENCE,
            gap_key="unsupported_row",
        ),
        owner_stage="claim",
        blocking_stages=("claim", "economics"),
        scope_kind="claim_scope",
        scope_ref="scope-1",
        subject_ref=None,
        gap_kind=GapKind.MISSING_EVIDENCE,
        gap_key="unsupported_row",
        status=GapStatus.OPEN,
        materiality=GapMateriality.MATERIAL,
        confidence=GapConfidence.HIGH,
    )
    review = ReviewRecord(
        review_id=stable_review_id(
            owner_stage="claim",
            scope_kind="claim_scope",
            scope_ref="scope-1",
            review_kind="advisory_mapping",
            review_key="fee_allocation",
        ),
        owner_stage="claim",
        scope_kind="claim_scope",
        scope_ref="scope-1",
        subject_ref=None,
        review_kind="advisory_mapping",
        review_key="fee_allocation",
        status=ReviewStatus.OPEN,
        confidence=ReviewConfidence.MEDIUM,
        gap_ids=("gap-b", "gap-a"),
    )

    assert set(gap.to_payload()) == {
        "gap_id",
        "owner_stage",
        "blocking_stages",
        "scope_kind",
        "scope_ref",
        "subject_ref",
        "gap_kind",
        "gap_key",
        "status",
        "materiality",
        "confidence",
    }
    assert set(review.to_payload()) == {
        "review_id",
        "owner_stage",
        "scope_kind",
        "scope_ref",
        "subject_ref",
        "review_kind",
        "review_key",
        "status",
        "confidence",
        "gap_ids",
    }
    assert review.to_payload()["gap_ids"] == ["gap-a", "gap-b"]


def test_assessment_ordering_and_explanation_serialization_are_deterministic() -> None:
    gap_records = canonical_gap_records(
        (
            GapRecord(
                gap_id="gap-2",
                owner_stage="claim",
                blocking_stages=("economics",),
                scope_kind="claim_scope",
                scope_ref="scope-2",
                subject_ref=None,
                gap_kind=GapKind.CONTRADICTION,
                gap_key="contradiction",
                status=GapStatus.OPEN,
                materiality=GapMateriality.MATERIAL,
                confidence=GapConfidence.LOW,
            ),
            GapRecord(
                gap_id="gap-1",
                owner_stage="claim",
                blocking_stages=("claim",),
                scope_kind="claim_scope",
                scope_ref="scope-1",
                subject_ref=None,
                gap_kind=GapKind.MISSING_EVIDENCE,
                gap_key="missing",
                status=GapStatus.OPEN,
                materiality=GapMateriality.SUPPORTING,
                confidence=GapConfidence.HIGH,
            ),
        )
    )
    review_records = canonical_review_records(
        (
            ReviewRecord(
                review_id="review-2",
                owner_stage="claim",
                scope_kind="claim_scope",
                scope_ref="scope-2",
                subject_ref=None,
                review_kind="mapping",
                review_key="fee",
                status=ReviewStatus.ACKNOWLEDGED,
                confidence=ReviewConfidence.LOW,
                gap_ids=(),
            ),
            ReviewRecord(
                review_id="review-1",
                owner_stage="claim",
                scope_kind="claim_scope",
                scope_ref="scope-1",
                subject_ref=None,
                review_kind="mapping",
                review_key="location",
                status=ReviewStatus.OPEN,
                confidence=ReviewConfidence.HIGH,
                gap_ids=("gap-1",),
            ),
        )
    )
    gap_explanation = GapExplanation(
        gap_id="gap-1",
        known_facts=("fact-b", "fact-a"),
        missing_inputs=("input-b", "input-a"),
        possible_meanings=("meaning-1",),
        required_evidence=("evidence-1",),
        resolution_options=("option-1",),
        next_action="inspect row",
        provenance_refs=("prov-b", "prov-a"),
    )
    review_explanation = ReviewExplanation(
        review_id="review-1",
        headline="Needs review",
        known_facts=("fact-b", "fact-a"),
        follow_up=("follow-up-b", "follow-up-a"),
        provenance_refs=("prov-b", "prov-a"),
    )

    assert tuple(record.gap_id for record in gap_records) == ("gap-1", "gap-2")
    assert tuple(record.review_id for record in review_records) == (
        "review-1",
        "review-2",
    )
    assert gap_explanation.to_payload()["provenance_refs"] == ["prov-a", "prov-b"]
    assert review_explanation.to_payload()["provenance_refs"] == ["prov-a", "prov-b"]
    assert gap_records_payload(gap_records) == [
        record.to_payload() for record in gap_records
    ]
    assert gap_explanations_payload((gap_explanation,)) == [
        gap_explanation.to_payload()
    ]
    assert review_records_payload(review_records) == [
        record.to_payload() for record in review_records
    ]
    assert review_explanations_payload((review_explanation,)) == [
        review_explanation.to_payload()
    ]
    assert ASSESSMENT_SCHEMA_VERSION == 1


def test_assessment_payload_helpers_preserve_deterministic_empty_arrays() -> None:
    assert gap_records_payload(()) == []
    assert gap_explanations_payload(()) == []
    assert review_records_payload(()) == []
    assert review_explanations_payload(()) == []


def test_assessment_records_require_non_empty_claim_scope_ref() -> None:
    with pytest.raises(ValueError, match="claim_scope gap records require scope_ref"):
        GapRecord(
            gap_id="gap-1",
            owner_stage="claim",
            blocking_stages=("claim",),
            scope_kind="claim_scope",
            scope_ref="",
            subject_ref=None,
            gap_kind=GapKind.MISSING_EVIDENCE,
            gap_key="missing",
            status=GapStatus.OPEN,
            materiality=GapMateriality.MATERIAL,
            confidence=GapConfidence.HIGH,
        )
    with pytest.raises(
        ValueError, match="claim_scope review records require scope_ref"
    ):
        ReviewRecord(
            review_id="review-1",
            owner_stage="claim",
            scope_kind="claim_scope",
            scope_ref=None,
            subject_ref=None,
            review_kind="mapping",
            review_key="fee",
            status=ReviewStatus.OPEN,
            confidence=ReviewConfidence.HIGH,
            gap_ids=(),
        )
