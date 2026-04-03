"""Shared timezone profile summaries for adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from tallylot.domain.issues import IssueRecord
from tallylot.domain.types import JsonValue
from tallylot.ports.source_profiles import SourceProfile

from .issues import IssueSpec, issue_record


@dataclass(frozen=True)
class TimezoneReviewPolicy:
    adapter_id: str
    mode: str
    message: str
    issue_kind: str = "timezone_review_required"
    severity: str = "high"


def passed_timezone_summary(
    profile: SourceProfile,
    *,
    mode: str,
) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
    rows_with_dates = sum(1 for item in profile.file_inventory if item.date_field)
    return {
        "status": "passed",
        "issue_count": 0,
        "rows_with_dates": rows_with_dates,
        "mode_counts": {mode: rows_with_dates} if rows_with_dates else {},
    }, ()


def reviewed_timezone_summary(
    profile: SourceProfile,
    *,
    policy: TimezoneReviewPolicy,
) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
    issues = tuple(
        issue_record(
            IssueSpec(
                issue_id=f"{policy.adapter_id}:{item.relative_path}:timezone",
                source=str(profile.source),
                adapter_id=policy.adapter_id,
                severity=policy.severity,
                kind=policy.issue_kind,
                message=policy.message,
                raw_file=item.relative_path,
            )
        )
        for item in profile.file_inventory
        if item.date_field and item.timezone_mode == "naive"
    )
    rows_with_dates = sum(1 for item in profile.file_inventory if item.date_field)
    mode_counts: dict[str, int] = {}
    for item in profile.file_inventory:
        if not item.date_field:
            continue
        mode_key = item.timezone_mode or policy.mode
        mode_counts[mode_key] = mode_counts.get(mode_key, 0) + 1
    return {
        "status": "needs_review" if issues else "passed",
        "issue_count": len(issues),
        "rows_with_dates": rows_with_dates,
        "mode_counts": cast(dict[str, JsonValue], dict(mode_counts)),
    }, issues
