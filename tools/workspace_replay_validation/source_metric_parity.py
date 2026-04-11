from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .models import ExpectedMetricDifference, SourceMetrics

SourceMetricField = Literal[
    "fact_count",
    "balance_count",
    "balance_evidence_count",
    "issue_count",
    "review_count",
]
ExpectedDeltaField = Literal["issue_count_delta", "review_count_delta"]


@dataclass(frozen=True)
class SourceMetricComparison:
    status: str
    row: dict[str, str]

    @property
    def is_mismatch(self) -> bool:
        return self.status == "mismatch"

    @property
    def uses_expected_difference(self) -> bool:
        return self.status == "expected_difference"


def build_source_metric_row(
    *,
    source: str,
    reference_metric: SourceMetrics | None,
    candidate_metric: SourceMetrics | None,
    expected_difference: ExpectedMetricDifference | None,
) -> SourceMetricComparison:
    hard_metrics_match = _hard_source_metrics_match(
        reference_metric,
        candidate_metric,
    )
    issue_count_status = _count_status(
        _count_delta(reference_metric, candidate_metric, "issue_count"),
        _expected_delta(expected_difference, "issue_count_delta"),
    )
    review_count_status = _count_status(
        _count_delta(reference_metric, candidate_metric, "review_count"),
        _expected_delta(expected_difference, "review_count_delta"),
    )
    status = _source_metric_status(
        hard_metrics_match=hard_metrics_match,
        issue_count_status=issue_count_status,
        review_count_status=review_count_status,
    )
    return SourceMetricComparison(
        status=status,
        row={
            "source": source,
            "status": status,
            "hard_metric_status": "match" if hard_metrics_match else "mismatch",
            "issue_count_status": issue_count_status,
            "review_count_status": review_count_status,
            "reference_fact_count": _source_metric_value(
                reference_metric, "fact_count"
            ),
            "candidate_fact_count": _source_metric_value(
                candidate_metric, "fact_count"
            ),
            "reference_balance_count": _source_metric_value(
                reference_metric, "balance_count"
            ),
            "candidate_balance_count": _source_metric_value(
                candidate_metric, "balance_count"
            ),
            "reference_balance_evidence_count": _source_metric_value(
                reference_metric, "balance_evidence_count"
            ),
            "candidate_balance_evidence_count": _source_metric_value(
                candidate_metric, "balance_evidence_count"
            ),
            "reference_issue_count": _source_metric_value(
                reference_metric, "issue_count"
            ),
            "candidate_issue_count": _source_metric_value(
                candidate_metric, "issue_count"
            ),
            "reference_review_count": _source_metric_value(
                reference_metric, "review_count"
            ),
            "candidate_review_count": _source_metric_value(
                candidate_metric, "review_count"
            ),
            "expected_issue_count_delta": str(
                _expected_delta(expected_difference, "issue_count_delta")
            ),
            "expected_review_count_delta": str(
                _expected_delta(expected_difference, "review_count_delta")
            ),
            "expected_difference_reason": _expected_reason(
                expected_difference,
                status,
            ),
        },
    )


def _source_metric_value(
    metric: SourceMetrics | None,
    field_name: SourceMetricField,
) -> str:
    if metric is None:
        return ""
    if field_name == "fact_count":
        return str(metric.fact_count)
    if field_name == "balance_count":
        return str(metric.balance_count)
    if field_name == "balance_evidence_count":
        return str(metric.balance_evidence_count)
    if field_name == "issue_count":
        return str(metric.issue_count)
    return str(metric.review_count)


def _hard_source_metrics_match(
    reference_metric: SourceMetrics | None,
    candidate_metric: SourceMetrics | None,
) -> bool:
    return (
        reference_metric is not None
        and candidate_metric is not None
        and reference_metric.fact_count == candidate_metric.fact_count
        and reference_metric.balance_count == candidate_metric.balance_count
        and reference_metric.balance_evidence_count
        == candidate_metric.balance_evidence_count
    )


def _count_delta(
    reference_metric: SourceMetrics | None,
    candidate_metric: SourceMetrics | None,
    field_name: Literal["issue_count", "review_count"],
) -> int | None:
    if reference_metric is None or candidate_metric is None:
        return None
    if field_name == "issue_count":
        reference_value = reference_metric.issue_count
        candidate_value = candidate_metric.issue_count
    else:
        reference_value = reference_metric.review_count
        candidate_value = candidate_metric.review_count
    return candidate_value - reference_value


def _count_status(
    actual_delta: int | None,
    expected_delta: int,
) -> str:
    if actual_delta is None:
        return "mismatch"
    if actual_delta == 0 and expected_delta == 0:
        return "match"
    if actual_delta == expected_delta:
        return "permitted_drift"
    return "mismatch"


def _source_metric_status(
    *,
    hard_metrics_match: bool,
    issue_count_status: str,
    review_count_status: str,
) -> str:
    if not hard_metrics_match:
        return "mismatch"
    count_statuses = {issue_count_status, review_count_status}
    if "mismatch" in count_statuses:
        return "mismatch"
    if "permitted_drift" in count_statuses:
        return "expected_difference"
    return "match"


def _expected_delta(
    expected_difference: ExpectedMetricDifference | None,
    field_name: ExpectedDeltaField,
) -> int:
    if expected_difference is None:
        return 0
    if field_name == "issue_count_delta":
        return expected_difference.issue_count_delta
    return expected_difference.review_count_delta


def _expected_reason(
    expected_difference: ExpectedMetricDifference | None,
    source_status: str,
) -> str:
    if expected_difference is None or source_status != "expected_difference":
        return ""
    return expected_difference.reason
