from __future__ import annotations

from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.types import CaptureUid
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.ports.evidence import ISSUE_HEADER, NORMALIZATION_REVIEW_HEADER


def test_issue_record_row_includes_raw_provenance_columns() -> None:
    record = IssueRecord(
        issue_id="binance:issue-1",
        source="binance",
        adapter_id="binance",
        severity="medium",
        kind="unsupported_row",
        message="unsupported row",
        raw_file="statement.pdf",
        raw_row_ref="row:2",
        raw_provenance=ProvenanceLocator(
            capture_uid=CaptureUid("01HV4A5H7VJH7M3Y5A6B7C8D9E"),
            relative_path="statement.pdf",
            locator_kind="raw_file",
        ),
    )

    row = record.to_row()

    assert tuple(row.keys()) == ISSUE_HEADER
    assert row["raw_file"] == "statement.pdf"
    assert row["raw_row_ref"] == "row:2"
    assert row["raw_capture_uid"] == "01HV4A5H7VJH7M3Y5A6B7C8D9E"
    assert row["raw_relative_path"] == "statement.pdf"


def test_review_record_row_includes_raw_provenance_columns() -> None:
    record = NormalizationReviewRecord(
        review_id="binance:review-1",
        source="binance",
        adapter_id="binance",
        scope="row",
        kind="unsupported_row",
        message="unsupported row",
        raw_file="statement.pdf",
        raw_row_ref="row:2",
        raw_provenance=ProvenanceLocator(
            capture_uid=CaptureUid("01HV4A5H7VJH7M3Y5A6B7C8D9E"),
            relative_path="statement.pdf",
            locator_kind="raw_file",
        ),
    )

    row = record.to_row()

    assert tuple(row.keys()) == NORMALIZATION_REVIEW_HEADER
    assert row["raw_row_ref"] == "row:2"
    assert row["raw_capture_uid"] == "01HV4A5H7VJH7M3Y5A6B7C8D9E"
