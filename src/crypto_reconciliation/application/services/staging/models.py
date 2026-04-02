"""Staging workflow models."""

from __future__ import annotations

from dataclasses import dataclass

from crypto_reconciliation.application.services.overlap import OverlapResult
from crypto_reconciliation.domain.models import IssueRecord


@dataclass(frozen=True)
class ScreeningResult:
    candidate_rows: int
    issues: tuple[IssueRecord, ...]
    duplicate_count: int
    has_time_overlap: bool
    overlap_result: OverlapResult | None = None

    @property
    def passed(self) -> bool:
        overlap_flagged = False if self.overlap_result is None else bool(self.overlap_result.summary["rows_flagged"])
        return not self.issues and self.duplicate_count == 0 and not self.has_time_overlap and not overlap_flagged

    @property
    def blocked_reason_codes(self) -> tuple[str, ...]:
        reasons: list[str] = []
        if self.issues:
            reasons.append("candidate_validation_failed")
        if self.duplicate_count:
            reasons.append("duplicate_tx_id")
        if self.has_time_overlap:
            reasons.append("time_overlap")
        if self.overlap_result is not None and self.overlap_result.summary["rows_flagged"]:
            reasons.append("overlap_review_required")
        return tuple(reasons)
