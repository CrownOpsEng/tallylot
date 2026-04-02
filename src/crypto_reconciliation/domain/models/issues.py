"""Issue and review record models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IssueRecord:
    issue_id: str
    source: str
    adapter_id: str
    severity: str
    kind: str
    message: str
    context_timestamp: str = ""
    raw_file: str = ""
    raw_row_ref: str = ""
    status: str = "open"

    def to_row(self) -> dict[str, str]:
        return {
            "issue_id": self.issue_id,
            "source": self.source,
            "adapter_id": self.adapter_id,
            "severity": self.severity,
            "kind": self.kind,
            "message": self.message,
            "context_timestamp": self.context_timestamp,
            "raw_file": self.raw_file,
            "raw_row_ref": self.raw_row_ref,
            "status": self.status,
        }


@dataclass(frozen=True)
class NormalizationReviewRecord:
    review_id: str
    source: str
    adapter_id: str
    scope: str
    kind: str
    message: str
    raw_file: str = ""
    raw_row_ref: str = ""
    field_name: str = ""
    original_value: str = ""
    normalized_value: str = ""
    status: str = "needs_review"

    def to_row(self) -> dict[str, str]:
        return {
            "review_id": self.review_id,
            "source": self.source,
            "adapter_id": self.adapter_id,
            "scope": self.scope,
            "kind": self.kind,
            "message": self.message,
            "raw_file": self.raw_file,
            "raw_row_ref": self.raw_row_ref,
            "field_name": self.field_name,
            "original_value": self.original_value,
            "normalized_value": self.normalized_value,
            "status": self.status,
        }
