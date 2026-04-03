#!/usr/bin/env python3

"""Shared timestamp and tabular-analysis helpers for CSV and workbook inspection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, tzinfo
from typing import Iterable, Sequence

from script_common import parse_datetime, parse_datetime_to_utc_naive, source_timezone_from_filename, tzinfo_label


DATE_FIELD_PATTERN = ("date", "time", "timestamp", "created at", "operation date", "settlement_date", "transaction_date")
DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S UTC",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
    "%d.%m.%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S+00",
)


@dataclass(frozen=True)
class TimestampEvidence:
    value: datetime
    fmt: str
    resolution: str
    timezone_mode: str
    timezone_value: str


@dataclass
class DateFieldStats:
    count: int = 0
    min_value: datetime | None = None
    max_value: datetime | None = None
    first_resolution: str = ""
    resolution_values: set[str] | None = None
    first_timezone_mode: str = ""
    timezone_modes: set[str] | None = None
    first_timezone_value: str = ""
    timezone_values: set[str] | None = None

    def __post_init__(self) -> None:
        if self.resolution_values is None:
            self.resolution_values = set()
        if self.timezone_modes is None:
            self.timezone_modes = set()
        if self.timezone_values is None:
            self.timezone_values = set()

    def update(self, evidence: TimestampEvidence) -> None:
        self.count += 1
        self.min_value = evidence.value if self.min_value is None else min(self.min_value, evidence.value)
        self.max_value = evidence.value if self.max_value is None else max(self.max_value, evidence.value)
        if not self.first_resolution:
            self.first_resolution = evidence.resolution
        if not self.first_timezone_mode:
            self.first_timezone_mode = evidence.timezone_mode
        if not self.first_timezone_value:
            self.first_timezone_value = evidence.timezone_value
        self.resolution_values.add(evidence.resolution)
        self.timezone_modes.add(evidence.timezone_mode)
        if evidence.timezone_value:
            self.timezone_values.add(evidence.timezone_value)


@dataclass(frozen=True)
class TabularAnalysis:
    header: tuple[str, ...]
    header_index: int
    date_field: str
    min_timestamp: str
    max_timestamp: str
    row_count: int
    timestamp_resolution: str
    timezone_mode: str
    timezone_value: str
    timezone_conflict: str


def detect_header_from_rows(rows: Sequence[Sequence[str]], *, sample_size: int = 10) -> tuple[list[str], int]:
    best_index = -1
    best_row: list[str] = []
    for index, row in enumerate(rows[:sample_size]):
        width = len([cell for cell in row if cell.strip()])
        if width > len(best_row):
            best_row = list(row)
            best_index = index
    return best_row, best_index


def _header_timezone_hint(header: Sequence[str], date_field: str) -> tuple[str, str]:
    joined = " | ".join(column.strip().lower() for column in header)
    field = date_field.strip().lower()
    if "utc" in field or "utc" in joined:
        return "header_utc", "UTC"
    return "", ""


def _timestamp_resolution_for_format(fmt: str) -> str:
    if "%H" not in fmt and "%I" not in fmt:
        return "date_only"
    if "%f" in fmt:
        return "subsecond"
    return "second"


def _timezone_evidence_for_format(
    fmt: str,
    parsed: datetime,
    *,
    source_timezone: tzinfo | None = None,
) -> tuple[str, str]:
    if "%z" in fmt:
        return "value_offset", tzinfo_label(parsed.tzinfo)
    if "UTC" in fmt or fmt.endswith("Z"):
        return "value_utc", "UTC"
    if _timestamp_resolution_for_format(fmt) == "date_only":
        return "date_only", ""
    if source_timezone is not None:
        return "source_timezone", tzinfo_label(source_timezone)
    return "naive", ""


def parse_candidate_timestamp_evidence(value: str, *, source_timezone: tzinfo | None = None) -> TimestampEvidence | None:
    text = value.strip()
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            parsed = parse_datetime(text, (fmt,))
        except ValueError:
            continue
        timezone_mode, timezone_value = _timezone_evidence_for_format(fmt, parsed, source_timezone=source_timezone)
        return TimestampEvidence(
            value=parse_datetime_to_utc_naive(text, (fmt,), source_timezone=source_timezone),
            fmt=fmt,
            resolution=_timestamp_resolution_for_format(fmt),
            timezone_mode=timezone_mode,
            timezone_value=timezone_value,
        )
    return None


def parse_candidate_timestamp(value: str, *, source_timezone: tzinfo | None = None) -> datetime | None:
    evidence = parse_candidate_timestamp_evidence(value, source_timezone=source_timezone)
    return evidence.value if evidence is not None else None


def _finalize_timezone_metadata(
    *,
    filename: str,
    header: Sequence[str],
    date_field: str,
    parsed_values: Sequence[TimestampEvidence],
) -> tuple[str, str, str, str]:
    if not parsed_values:
        return "", "", "", ""

    resolution = parsed_values[0].resolution if len({item.resolution for item in parsed_values}) == 1 else "mixed"
    header_mode, header_value = _header_timezone_hint(header, date_field)
    filename_timezone = source_timezone_from_filename(filename)
    filename_mode = "filename_offset" if filename_timezone is not None else ""
    filename_value = tzinfo_label(filename_timezone)
    evidence_mode = parsed_values[0].timezone_mode if len({item.timezone_mode for item in parsed_values}) == 1 else "mixed"
    evidence_value = parsed_values[0].timezone_value if len({item.timezone_value for item in parsed_values}) == 1 else "mixed"

    hints = [
        (mode, value)
        for mode, value in ((header_mode, header_value), (filename_mode, filename_value), (evidence_mode, evidence_value))
        if mode
    ]
    distinct_values = {value for _, value in hints if value}
    if len(distinct_values) > 1:
        return resolution, "conflict", " | ".join(sorted(distinct_values)), "yes"

    if evidence_mode in {"value_utc", "value_offset"}:
        return resolution, evidence_mode, evidence_value, ""
    if filename_mode:
        return resolution, filename_mode, filename_value, ""
    if header_mode:
        return resolution, header_mode, header_value, ""
    return resolution, evidence_mode, evidence_value, ""


def analyze_tabular_rows(
    *,
    filename: str,
    header: Sequence[str],
    header_index: int,
    rows: Iterable[Sequence[str]],
) -> TabularAnalysis:
    if header_index < 0 or not header:
        return TabularAnalysis(tuple(), -1, "", "", "", 0, "", "", "", "")

    date_field = ""
    candidates = [field for field in header if any(token in field.lower() for token in DATE_FIELD_PATTERN)]
    source_timezone = source_timezone_from_filename(filename)
    stats_by_field = {field: DateFieldStats() for field in candidates}
    row_count = 0

    for row in rows:
        if not any(cell.strip() for cell in row):
            continue
        if len(row) == 1 and row[0].strip().lower() == "no data matches the criteria.":
            continue
        row_count += 1
        if not candidates:
            continue
        normalized_row = {header[index]: (row[index] if index < len(row) else "") for index in range(len(header))}
        for field in candidates:
            evidence = parse_candidate_timestamp_evidence(
                (normalized_row.get(field) or "").strip(),
                source_timezone=source_timezone,
            )
            if evidence is not None:
                stats_by_field[field].update(evidence)

    best_count = -1
    best_stats: DateFieldStats | None = None
    for field in candidates:
        stats = stats_by_field[field]
        if stats.count > best_count:
            best_count = stats.count
            best_stats = stats
            date_field = field

    if best_stats is None or best_stats.count == 0:
        if row_count == 0:
            return TabularAnalysis(tuple(header), header_index, "", "", "", 0, "", "", "", "")
        return TabularAnalysis(tuple(header), header_index, date_field, "", "", row_count, "", "", "", "")

    parsed_values: list[TimestampEvidence]
    if len(best_stats.resolution_values) <= 1 and len(best_stats.timezone_modes) <= 1 and len(best_stats.timezone_values) <= 1:
        parsed_values = [
            TimestampEvidence(
                value=best_stats.min_value or best_stats.max_value or datetime.min,
                fmt="",
                resolution=best_stats.first_resolution,
                timezone_mode=best_stats.first_timezone_mode,
                timezone_value=best_stats.first_timezone_value,
            )
        ]
    else:
        parsed_values = [
            TimestampEvidence(
                value=best_stats.min_value or datetime.min,
                fmt="",
                resolution=best_stats.first_resolution,
                timezone_mode=best_stats.first_timezone_mode,
                timezone_value=best_stats.first_timezone_value,
            ),
            TimestampEvidence(
                value=best_stats.max_value or datetime.min,
                fmt="",
                resolution=best_stats.first_resolution if len(best_stats.resolution_values) <= 1 else "mixed",
                timezone_mode=best_stats.first_timezone_mode if len(best_stats.timezone_modes) <= 1 else "mixed",
                timezone_value=best_stats.first_timezone_value if len(best_stats.timezone_values) <= 1 else "mixed",
            ),
        ]
    resolution, timezone_mode, timezone_value, timezone_conflict = _finalize_timezone_metadata(
        filename=filename,
        header=header,
        date_field=date_field,
        parsed_values=parsed_values,
    )
    return TabularAnalysis(
        header=tuple(header),
        header_index=header_index,
        date_field=date_field,
        min_timestamp=(best_stats.min_value or datetime.min).strftime("%Y-%m-%d %H:%M:%S"),
        max_timestamp=(best_stats.max_value or datetime.min).strftime("%Y-%m-%d %H:%M:%S"),
        row_count=row_count,
        timestamp_resolution=resolution,
        timezone_mode=timezone_mode,
        timezone_value=timezone_value,
        timezone_conflict=timezone_conflict,
    )
