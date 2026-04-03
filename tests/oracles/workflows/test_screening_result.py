from __future__ import annotations

from tallylot.domain.issues import IssueRecord
from tools.oracles.contracts import OverlapResult, ScreeningResult


def test_screening_result_passes_when_no_issues_duplicates_or_overlap() -> None:
    result = ScreeningResult(candidate_rows=1, issues=(), duplicate_count=0, has_time_overlap=False)

    assert result.passed is True
    assert not result.blocked_reason_codes


def test_screening_result_blocks_for_validation_duplicates_and_overlap() -> None:
    result = ScreeningResult(
        candidate_rows=2,
        issues=(
            IssueRecord(
                issue_id="candidate.csv:2:missing_date",
                source="batch_screen",
                adapter_id="cointracking_csv",
                severity="high",
                kind="missing_date",
                message="Candidate rows must include Date.",
                raw_file="candidate.csv",
                raw_row_ref="2",
            ),
        ),
        duplicate_count=1,
        has_time_overlap=True,
    )

    assert result.passed is False
    assert result.blocked_reason_codes == (
        "candidate_validation_failed",
        "duplicate_tx_id",
        "time_overlap",
    )


def test_screening_result_blocks_for_overlap_review_required() -> None:
    result = ScreeningResult(
        candidate_rows=1,
        issues=(),
        duplicate_count=0,
        has_time_overlap=False,
        overlap_result=OverlapResult(summary={"rows_flagged": 1}, flagged_rows=()),
    )

    assert result.passed is False
    assert result.blocked_reason_codes == ("overlap_review_required",)
