"""Shared timezone profile summaries for adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import cast

from tallylot.domain.issues import IssueRecord
from tallylot.domain.types import JsonValue
from tallylot.ports.source_profiles import FileInventoryEntry, SourceProfile

from .issues import IssueSpec, issue_record


@dataclass(frozen=True)
class TimezoneReviewPolicy:
    adapter_id: str
    mode: str
    message: str
    issue_kind: str = "timezone_review_required"
    severity: str = "high"
    accepted_modes: frozenset[str] = frozenset()


@dataclass(frozen=True)
class _TimezoneValidationSpec:
    adapter_id: str
    declared_mode: str
    accepted_modes: frozenset[str]
    review_required_modes: frozenset[str]
    review_message: str
    review_issue_kind: str
    review_severity: str


_SEMANTIC_MODE_ACCEPTED_INVENTORY_MODES: dict[str, frozenset[str]] = {
    "america_toronto": frozenset({"naive"}),
    "date_only": frozenset({"date_only"}),
    "header_utc": frozenset({"header_utc", "value_utc"}),
    "naive": frozenset({"naive"}),
    "value_utc": frozenset({"header_utc", "value_utc"}),
}


def passed_timezone_summary(
    profile: SourceProfile,
    *,
    mode: str,
) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
    accepted_modes = _accepted_inventory_modes(mode)
    return _validate_timezone_inventory(
        profile,
        _TimezoneValidationSpec(
            adapter_id=str(profile.adapter_id),
            declared_mode=mode,
            accepted_modes=accepted_modes,
            review_required_modes=frozenset(),
            review_message="",
            review_issue_kind="timezone_review_required",
            review_severity="high",
        ),
    )


def reviewed_timezone_summary(
    profile: SourceProfile,
    *,
    policy: TimezoneReviewPolicy,
) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
    accepted_modes = (
        policy.accepted_modes
        if policy.accepted_modes
        else _accepted_inventory_modes(policy.mode) - {policy.mode}
    )
    return _validate_timezone_inventory(
        profile,
        _TimezoneValidationSpec(
            adapter_id=policy.adapter_id,
            declared_mode=policy.mode,
            accepted_modes=accepted_modes,
            review_required_modes=frozenset({policy.mode}),
            review_message=policy.message,
            review_issue_kind=policy.issue_kind,
            review_severity=policy.severity,
        ),
    )


def _validate_timezone_inventory(
    profile: SourceProfile,
    spec: _TimezoneValidationSpec,
) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
    dated_items = tuple(item for item in profile.file_inventory if item.date_field)
    rows_with_dates = sum(1 for item in profile.file_inventory if item.date_field)
    mode_counts: dict[str, int] = {}
    timezone_values: dict[str, int] = {}
    issues: list[IssueRecord] = []
    for item in dated_items:
        mode_key = item.timezone_mode or spec.declared_mode or "unknown"
        mode_counts[mode_key] = mode_counts.get(mode_key, 0) + 1
        if item.timezone_value:
            timezone_values[item.timezone_value] = (
                timezone_values.get(item.timezone_value, 0) + 1
            )
        issue = _inventory_timezone_issue(profile, spec, item)
        if issue is not None:
            issues.append(issue)
    issues.extend(_timezone_shift_overlap_issues(profile, adapter_id=spec.adapter_id))
    return {
        "status": "needs_review" if issues else "passed",
        "issue_count": len(issues),
        "rows_with_dates": rows_with_dates,
        "mode_counts": cast(dict[str, JsonValue], dict(mode_counts)),
        "declared_mode": spec.declared_mode,
        "accepted_modes": list(sorted(spec.accepted_modes)),
        "timezone_values": cast(dict[str, JsonValue], dict(timezone_values)),
    }, tuple(issues)


def _inventory_timezone_issue(
    profile: SourceProfile,
    spec: _TimezoneValidationSpec,
    entry: FileInventoryEntry,
) -> IssueRecord | None:
    if entry.timezone_conflict:
        return issue_record(
            IssueSpec(
                issue_id=f"{spec.adapter_id}:{entry.relative_path}:timezone_conflict",
                source=str(profile.source),
                adapter_id=spec.adapter_id,
                severity="high",
                kind="timezone_conflict_detected",
                message=(
                    "Profiled timestamp metadata conflicts with the observed timestamp "
                    f"values: {entry.timezone_conflict}."
                ),
                raw_file=entry.relative_path,
            )
        )
    mode = entry.timezone_mode
    if mode in spec.review_required_modes:
        return issue_record(
            IssueSpec(
                issue_id=f"{spec.adapter_id}:{entry.relative_path}:timezone",
                source=str(profile.source),
                adapter_id=spec.adapter_id,
                severity=spec.review_severity,
                kind=spec.review_issue_kind,
                message=spec.review_message,
                raw_file=entry.relative_path,
            )
        )
    if mode and mode not in spec.accepted_modes:
        return issue_record(
            IssueSpec(
                issue_id=f"{spec.adapter_id}:{entry.relative_path}:unexpected_timezone_mode",
                source=str(profile.source),
                adapter_id=spec.adapter_id,
                severity="high",
                kind="timezone_mode_unexpected",
                message=(
                    f"Profiled timezone mode {mode!r} is not accepted for this adapter. "
                    f"Expected one of {', '.join(sorted(spec.accepted_modes)) or spec.declared_mode!r}."
                ),
                raw_file=entry.relative_path,
            )
        )
    if not mode and spec.declared_mode:
        return issue_record(
            IssueSpec(
                issue_id=f"{spec.adapter_id}:{entry.relative_path}:missing_timezone_mode",
                source=str(profile.source),
                adapter_id=spec.adapter_id,
                severity="high",
                kind="timezone_mode_missing",
                message=(
                    "The profiled file contains dated rows but no timezone mode could be "
                    "determined from the export."
                ),
                raw_file=entry.relative_path,
            )
        )
    return None


def _timezone_shift_overlap_issues(
    profile: SourceProfile,
    *,
    adapter_id: str,
) -> list[IssueRecord]:
    issues: list[IssueRecord] = []
    dated_items = tuple(
        item
        for item in profile.file_inventory
        if (
            item.date_field
            and item.family
            and item.timezone_value
            and item.min_timestamp
            and item.max_timestamp
        )
    )
    for index, left in enumerate(dated_items):
        for right in dated_items[index + 1 :]:
            if not _timezone_shift_overlap(left, right):
                continue
            issues.append(
                issue_record(
                    IssueSpec(
                        issue_id=(
                            f"{adapter_id}:{left.relative_path}:{right.relative_path}:"
                            "timezone_shift_overlap"
                        ),
                        source=str(profile.source),
                        adapter_id=adapter_id,
                        severity="high",
                        kind="timezone_shift_overlap_review_required",
                        message=(
                            "Profiled exports in the same family overlap in UTC after "
                            f"timezone normalization but declare different timezone values "
                            f"({left.timezone_value} vs {right.timezone_value}). This can "
                            "duplicate or reorder data and must be reviewed before normalization."
                        ),
                        raw_file=left.relative_path,
                    )
                )
            )
    return issues


def _timezone_shift_overlap(
    left_entry: FileInventoryEntry,
    right_entry: FileInventoryEntry,
) -> bool:
    if left_entry.family != right_entry.family:
        return False
    if left_entry.timezone_value == right_entry.timezone_value:
        return False
    left_start = _parse_profile_timestamp(left_entry.min_timestamp)
    left_end = _parse_profile_timestamp(left_entry.max_timestamp)
    right_start = _parse_profile_timestamp(right_entry.min_timestamp)
    right_end = _parse_profile_timestamp(right_entry.max_timestamp)
    if (
        left_start is None
        or left_end is None
        or right_start is None
        or right_end is None
    ):
        return False
    return left_start <= right_end and right_start <= left_end


def _accepted_inventory_modes(mode: str) -> frozenset[str]:
    accepted = _SEMANTIC_MODE_ACCEPTED_INVENTORY_MODES.get(mode)
    if accepted is not None:
        return accepted
    return frozenset({mode})


def _parse_profile_timestamp(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
