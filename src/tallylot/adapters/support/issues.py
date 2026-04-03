"""Shared issue and review factories for adapters."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord


@dataclass(frozen=True)
class IssueSpec:
    issue_id: str
    source: str
    adapter_id: str
    kind: str
    message: str
    severity: str = "medium"
    context_timestamp: str = ""
    raw_file: str = ""
    raw_row_ref: str = ""
    status: str = "open"


@dataclass(frozen=True)
class ReviewSpec:
    review_id: str
    source: str
    adapter_id: str
    scope: str
    kind: str
    message: str
    context_timestamp: str = ""
    raw_file: str = ""
    raw_row_ref: str = ""
    field_name: str = ""
    original_value: str = ""
    normalized_value: str = ""
    status: str = "needs_review"


def issue_record(spec: IssueSpec) -> IssueRecord:
    return IssueRecord(
        issue_id=spec.issue_id,
        source=spec.source,
        adapter_id=spec.adapter_id,
        severity=spec.severity,
        kind=spec.kind,
        message=spec.message,
        context_timestamp=spec.context_timestamp,
        raw_file=spec.raw_file,
        raw_row_ref=spec.raw_row_ref,
        status=spec.status,
    )


def review_record(spec: ReviewSpec) -> NormalizationReviewRecord:
    return NormalizationReviewRecord(
        review_id=spec.review_id,
        source=spec.source,
        adapter_id=spec.adapter_id,
        scope=spec.scope,
        kind=spec.kind,
        message=spec.message,
        context_timestamp=spec.context_timestamp,
        raw_file=spec.raw_file,
        raw_row_ref=spec.raw_row_ref,
        field_name=spec.field_name,
        original_value=spec.original_value,
        normalized_value=spec.normalized_value,
        status=spec.status,
    )
