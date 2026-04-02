"""Structured CSV issue and review builders."""

from __future__ import annotations

from dataclasses import dataclass

from crypto_reconciliation.domain.issues import IssueRecord, NormalizationReviewRecord
from crypto_reconciliation.ports.source_profiles import SourceProfile

from .contracts import TRANSACTIONS_FILENAME, ReviewSpec


@dataclass(frozen=True)
class StructuredCsvFeedbackFactory:
    profile: SourceProfile
    adapter_id: str

    def issue(
        self,
        index: int,
        kind: str,
        message: str,
    ) -> IssueRecord:
        return IssueRecord(
            issue_id=f"{self.profile.source}:{index}:{kind}",
            source=str(self.profile.source),
            adapter_id=self.adapter_id,
            severity="high",
            kind=kind,
            message=message,
            raw_file=TRANSACTIONS_FILENAME,
            raw_row_ref=str(index),
        )

    def dataset_review(self, kind: str, message: str) -> NormalizationReviewRecord:
        return self.review(index=None, spec=ReviewSpec(kind=kind, message=message))

    def review(
        self,
        *,
        index: int | None,
        spec: ReviewSpec,
    ) -> NormalizationReviewRecord:
        review_id = (
            f"{self.profile.source}:{index}:{spec.kind}"
            if index is not None
            else f"{self.profile.source}:dataset:{spec.kind}"
        )
        return NormalizationReviewRecord(
            review_id=review_id,
            source=str(self.profile.source),
            adapter_id=self.adapter_id,
            scope="row" if index is not None else "dataset",
            kind=spec.kind,
            message=spec.message,
            raw_file=TRANSACTIONS_FILENAME,
            raw_row_ref="" if index is None else str(index),
            field_name=spec.values.field_name,
            original_value=spec.values.original_value,
            normalized_value=spec.values.normalized_value,
        )
