"""Capture and source lifecycle reducers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from tallylot.domain.types import SourceId
from tallylot.ports.captures import SourceInventorySummaryRecord

_BLOCKED_CAPTURE_STATUSES = frozenset(
    {"capture_blocked", "duplicate_blocked", "overlap_review_required", "superseded"}
)


@dataclass(frozen=True)
class SourceInventorySummaryReduction:
    source: str
    capture_rows: list[dict[str, str]]
    source_rows: list[dict[str, str]]
    requested_status: str | None = None
    assembled_root_ref: str | None = None
    assembled_output_present: bool | None = None
    assembly_excluded_capture_count: int | None = None


def reduce_capture_status(existing_status: str, requested_status: str) -> str:
    if requested_status == "profiled" and existing_status in {
        "normalized",
        "assembly_included",
        "assembly_excluded",
    }:
        return existing_status
    if requested_status == "normalized" and existing_status in {
        "assembly_included",
        "assembly_excluded",
    }:
        return existing_status
    return requested_status


def reduce_source_inventory_summary(
    *,
    reduction: SourceInventorySummaryReduction,
) -> dict[str, str]:
    matching_by_uid = _latest_capture_rows_for_source(
        reduction.capture_rows, reduction.source
    )
    matching = tuple(matching_by_uid.values())
    history = tuple(
        row
        for row in reduction.capture_rows
        if row.get("source", "") == reduction.source
    )
    meaningful_rows = tuple(
        row for row in matching if row.get("status", "") != "duplicate_blocked"
    )
    latest = _latest_completed_capture_row(meaningful_rows or matching)
    existing_status = _existing_value(reduction.source_rows, reduction.source, "status")
    existing_assembly_status = _existing_value(
        reduction.source_rows, reduction.source, "assembly_status"
    )
    updated_row = SourceInventorySummaryRecord(
        source=SourceId(reduction.source),
        activity_after_cutoff=_existing_value(
            reduction.source_rows, reduction.source, "activity_after_cutoff"
        ),
        scope_status=_existing_value(
            reduction.source_rows, reduction.source, "scope_status"
        )
        or "in_scope",
        status=_reduce_source_status(
            existing_status,
            capture_history=history,
            requested_status=reduction.requested_status,
            assembled_output_present=reduction.assembled_output_present,
        ),
        capture_count=len(matching),
        latest_capture_uid=latest.get("capture_uid", ""),
        latest_capture_label=latest.get("capture_label", ""),
        latest_capture_completed_at=_parse_optional_timestamp(
            latest.get("intake_completed_at", "")
        ),
        assembly_status=_reduce_assembly_status(
            existing_assembly_status,
            matching,
            assembled_output_present=reduction.assembled_output_present,
            assembly_excluded_capture_count=(reduction.assembly_excluded_capture_count),
        ),
        assembled_root_ref=_reduce_assembled_root_ref(
            _existing_value(
                reduction.source_rows, reduction.source, "assembled_root_ref"
            ),
            assembled_root_ref=reduction.assembled_root_ref,
            assembled_output_present=reduction.assembled_output_present,
        ),
        adapter_hints=_existing_value(
            reduction.source_rows, reduction.source, "adapter_hints"
        ),
        notes=_existing_value(reduction.source_rows, reduction.source, "notes"),
    ).to_row()
    return updated_row


def _existing_value(rows: list[dict[str, str]], source: str, field: str) -> str:
    for row in rows:
        if row.get("source", "") == source:
            return row.get(field, "")
    return ""


def _reduce_source_status(
    existing_status: str,
    *,
    capture_history: tuple[dict[str, str], ...],
    requested_status: str | None,
    assembled_output_present: bool | None,
) -> str:
    if assembled_output_present is not None:
        return _reduce_assembly_source_status(
            existing_status,
            derived_status=_source_status_from_capture_history(
                capture_history,
                allow_assembled=assembled_output_present,
            ),
            assembled_output_present=assembled_output_present,
        )
    if requested_status is not None:
        return _higher_source_status(existing_status, requested_status)
    derived = _source_status_from_capture_history(capture_history)
    if existing_status in {"profiled", "normalized", "assembled"}:
        return existing_status
    return derived or existing_status


def _reduce_assembly_source_status(
    existing_status: str,
    *,
    derived_status: str,
    assembled_output_present: bool,
) -> str:
    if assembled_output_present:
        return "assembled"
    if existing_status == "assembled":
        return derived_status
    return _higher_source_status(existing_status, derived_status)


def _higher_source_status(first: str, second: str) -> str:
    if _source_status_rank(first) >= _source_status_rank(second):
        return first
    return second


def _source_status_from_capture_history(
    capture_history: tuple[dict[str, str], ...],
    *,
    allow_assembled: bool = True,
) -> str:
    statuses = {row.get("status", "") for row in capture_history}
    if allow_assembled and statuses & {"assembly_included"}:
        return "assembled"
    if statuses & {"normalized", "assembly_included", "assembly_excluded"}:
        return "normalized"
    if statuses & {"profiled"}:
        return "profiled"
    if any(status and status not in _BLOCKED_CAPTURE_STATUSES for status in statuses):
        return "capture_complete"
    if statuses:
        return ""
    return ""


def _reduce_assembly_status(
    existing_assembly_status: str,
    capture_rows: tuple[dict[str, str], ...],
    *,
    assembled_output_present: bool | None,
    assembly_excluded_capture_count: int | None,
) -> str:
    if assembled_output_present is True:
        return "assembled"
    if assembled_output_present is False:
        has_excluded_captures = (
            bool(capture_rows)
            if assembly_excluded_capture_count is None
            else assembly_excluded_capture_count > 0
        )
        if has_excluded_captures:
            return "excluded"
        return "pending"
    return existing_assembly_status or "pending"


def _reduce_assembled_root_ref(
    existing_root_ref: str,
    *,
    assembled_root_ref: str | None,
    assembled_output_present: bool | None,
) -> str:
    if assembled_output_present is True and assembled_root_ref is not None:
        return assembled_root_ref
    if assembled_output_present is False:
        return ""
    if assembled_root_ref is not None:
        return assembled_root_ref
    return existing_root_ref


def _source_status_rank(status: str) -> int:
    return {
        "": -1,
        "capture_complete": 0,
        "profiled": 1,
        "normalized": 2,
        "assembled": 3,
    }.get(status, -1)


def _latest_capture_rows_for_source(
    rows: list[dict[str, str]], source: str
) -> dict[str, dict[str, str]]:
    latest_by_uid: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("source", "") != source:
            continue
        capture_uid = row.get("capture_uid", "")
        if capture_uid:
            latest_by_uid[capture_uid] = row
    return latest_by_uid


def _latest_completed_capture_row(
    rows: tuple[dict[str, str], ...],
) -> dict[str, str]:
    if not rows:
        return {}
    return max(
        rows,
        key=lambda row: (
            _parse_optional_timestamp(row.get("intake_completed_at", ""))
            or datetime.min.replace(tzinfo=UTC),
            row.get("capture_label", ""),
            row.get("capture_uid", ""),
        ),
    )


def _parse_optional_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
