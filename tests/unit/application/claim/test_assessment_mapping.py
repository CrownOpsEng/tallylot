from __future__ import annotations

from tallylot.application.claim.assessment import (
    map_claim_issue_to_scope,
    map_claim_review_to_scope,
)
from tallylot.domain.claim import ClaimBundleDecisionOutcome
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord


def test_unsupported_selected_retail_row_maps_to_blocked_claim_scope_and_compatibility_issue() -> (
    None
):
    mapping = map_claim_issue_to_scope(
        issue=IssueRecord(
            issue_id="coinbase:retail.csv:row:4",
            source="coinbase",
            adapter_id="coinbase",
            severity="high",
            kind="unsupported_row",
            message="Unsupported Coinbase retail transaction type: Convert",
            raw_file="retail.csv",
            raw_row_ref="row:4",
        ),
        claim_set_id="claim-set-1",
        retail_member_id="member-1",
    )

    assert mapping is not None
    assert mapping.bundle_decision.outcome is ClaimBundleDecisionOutcome.BLOCKED
    assert mapping.gap_record.scope_kind == "claim_scope"
    assert mapping.compatibility_issue.kind == "unsupported_row"


def test_advisory_review_maps_to_review_record_and_compatibility_review() -> None:
    mapping = map_claim_review_to_scope(
        review=NormalizationReviewRecord(
            review_id="review-1",
            source="coinbase",
            adapter_id="coinbase",
            scope="translation",
            kind="fee_attribution",
            message="Fee allocation needs review",
            raw_file="retail.csv",
            raw_row_ref="row:4",
            field_name="fee",
            original_value="10",
            normalized_value="quote_leg",
        ),
        claim_set_id="claim-set-1",
        retail_member_id="member-1",
    )

    assert mapping is not None
    assert mapping.review_record.scope_kind == "claim_scope"
    assert mapping.compatibility_review.kind == "fee_attribution"


def test_selection_stage_blockers_do_not_create_claim_scope_assessment() -> None:
    assert (
        map_claim_issue_to_scope(
            issue=IssueRecord(
                issue_id="coinbase:missing_retail_csv",
                source="coinbase",
                adapter_id="coinbase",
                severity="high",
                kind="missing_required_input",
                message="Coinbase retail all-time CSV is required for deterministic normalization.",
            ),
            claim_set_id="claim-set-1",
            retail_member_id="member-1",
        )
        is None
    )
