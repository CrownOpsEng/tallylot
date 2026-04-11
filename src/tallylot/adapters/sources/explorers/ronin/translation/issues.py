"""Ronin explorer translation issue helpers."""

from __future__ import annotations

from tallylot.adapters.support import IssueSpec, issue_record
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.ports.source_profiles import SourceProfile

from .rows import RoninFeeResolution


def supported_fee_reviews(
    fee_resolution: RoninFeeResolution,
    *,
    draft_count: int,
) -> tuple[NormalizationReviewRecord, ...]:
    if draft_count == 0 or fee_resolution.review is None:
        return ()
    return (fee_resolution.review,)


def row_issue(
    profile: SourceProfile,
    raw_file: str,
    raw_row_ref: str,
    issue_id_suffix: str,
    message: str,
) -> IssueRecord:
    return issue_record(
        IssueSpec(
            issue_id=f"ronin:{raw_file}:{raw_row_ref}:{issue_id_suffix}",
            source=str(profile.source),
            adapter_id="ronin",
            kind="unsupported_row",
            message=message,
            raw_file=raw_file,
            raw_row_ref=raw_row_ref,
        )
    )
