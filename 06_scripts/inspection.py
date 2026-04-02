#!/usr/bin/env python3

"""Shared file inspection and historical-date inference helpers."""

from __future__ import annotations

import io
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from archive_handling import summarize_archive_members
from artifact_detection import detect_artifact
from file_family import classify_file_family
from html_inspection import inspect_html
from scope_identity import csv_scope_tokens, describe_scope_tokens, extract_scope_tokens, json_scope_tokens, token_from_header_value
from script_common import sniff_csv_dialect
from tabular_inspection import DATE_FORMATS, TimestampEvidence, analyze_tabular_rows, detect_header_from_rows, parse_candidate_timestamp, parse_candidate_timestamp_evidence
from workbook_inspection import inspect_workbook
EXPORT_DATE_PATTERNS = (
    re.compile(r"(?<!\d)(?P<date>\d{4}-\d{2}-\d{2})(?!\d)"),
    re.compile(r"(?<!\d)(?P<date>\d{4}\.\d{2}\.\d{2})(?!\d)"),
    re.compile(r"(?<!\d)(?P<date>\d{8})(?!\d)"),
)
DAY_MONTH_YEAR_PATTERN = re.compile(r"(?<!\d)(?P<first>\d{2})-(?P<second>\d{2})-(?P<year>20\d{2})(?!\d)")
COMPACT_TIMESTAMP_PATTERN = re.compile(r"(?<!\d)(?P<timestamp>\d{12}|\d{14})(?!\d)")
YEAR_MONTH_PATTERN = re.compile(r"(?P<year>20\d{2})[-_.](?P<month>\d{2})")
YEAR_PATTERN = re.compile(r"(?<!\d)(?P<year>20\d{2})(?!\d)")

@dataclass(frozen=True)
class HistoricalDateDecision:
    capture_id: str
    granularity: str
    basis: str
    review_required: bool = False


@dataclass(frozen=True)
class HistoricalDatePolicy:
    prefer_last_explicit: bool = True
    allow_content_span: bool = True
    allow_compact_timestamp: bool = True
    allow_year_month_context: bool = True
    allow_year_context: bool = True

def iter_csv_rows(path: Path) -> Iterable[list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        yield from csv.reader(handle, dialect=sniff_csv_dialect(path))


def detect_csv_header(path: Path) -> tuple[list[str], int]:
    best_index = -1
    best_row: list[str] = []
    for index, row in enumerate(iter_csv_rows(path)):
        if index >= 10:
            break
        width = len([cell for cell in row if cell.strip()])
        if width > len(best_row):
            best_row = row
            best_index = index
    if best_index == -1:
        return [], -1
    return best_row, best_index


def detect_csv_header_from_text(text: str) -> tuple[list[str], int]:
    rows = list(csv.reader(io.StringIO(text)))
    best_index = -1
    best_row: list[str] = []
    for index, row in enumerate(rows[:10]):
        width = len([cell for cell in row if cell.strip()])
        if width > len(best_row):
            best_row = row
            best_index = index
    if best_index == -1:
        return [], -1
    return best_row, best_index


def inspect_json_payload(path: Path) -> tuple[str, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "json", ""
    if isinstance(payload, dict):
        header_preview = " | ".join(str(key) for key in list(payload.keys())[:8])
        if isinstance(payload.get("metamask"), dict):
            return "metamask_state_json", header_preview
        return "json", header_preview
    return "json", type(payload).__name__


def inspect_json_scope_tokens(path: Path) -> frozenset[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return frozenset()
    return json_scope_tokens(payload)


def inspect_archive_payload(path: Path) -> tuple[str, str, dict[str, str]]:
    summary = summarize_archive_members(path, inspect_file)
    preview = summary.get("archive_member_preview", "")
    family_candidates = [item for item in summary.get("archive_member_families", "").split(";") if item]
    if len(set(family_candidates)) == 1 and family_candidates:
        return family_candidates[0], preview, summary
    if summary.get("archive_detected_source") == "CoinTracking":
        return "cointracking_archive_bundle", preview, summary
    if summary.get("archive_detected_source") == "Binance":
        return "binance_archive_bundle", preview, summary
    return "archive_bundle", preview, summary


def analyze_csv(path: Path) -> tuple[list[str], int, str, str, str, int, str, str, str, str]:
    sample_rows: list[list[str]] = []
    rows = iter_csv_rows(path)
    for _ in range(10):
        try:
            sample_rows.append(next(rows))
        except StopIteration:
            break

    header, header_index = detect_header_from_rows(sample_rows)
    if header_index == -1 or not header:
        return [], -1, "", "", "", 0, "", "", "", ""
    body_rows = [
        row
        for index, row in enumerate(sample_rows)
        if index > header_index and any(cell.strip() for cell in row) and not (len(row) == 1 and row[0].strip().lower() == "no data matches the criteria.")
    ]
    for row in rows:
        if not any(cell.strip() for cell in row):
            continue
        if len(row) == 1 and row[0].strip().lower() == "no data matches the criteria.":
            continue
        body_rows.append(row)
    analysis = analyze_tabular_rows(
        filename=path.name,
        header=header,
        header_index=header_index,
        rows=body_rows,
    )
    return (
        list(analysis.header),
        analysis.header_index,
        analysis.date_field,
        analysis.min_timestamp,
        analysis.max_timestamp,
        analysis.row_count,
        analysis.timestamp_resolution,
        analysis.timezone_mode,
        analysis.timezone_value,
        analysis.timezone_conflict,
    )


def inspect_csv_scope_tokens(path: Path, *, max_rows: int = 100) -> frozenset[str]:
    try:
        header, header_index = detect_csv_header(path)
    except OSError:
        return frozenset()
    if header_index < 0 or not header:
        return frozenset()
    family = classify_file_family(path, header)
    rows: list[dict[str, str]] = []
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle, dialect=sniff_csv_dialect(path))
            for index, row in enumerate(reader):
                if index <= header_index:
                    continue
                if not any(cell.strip() for cell in row):
                    continue
                if len(row) == 1 and row[0].strip().lower() == "no data matches the criteria.":
                    continue
                rows.append({header[column]: (row[column] if column < len(row) else "") for column in range(len(header))})
                if len(rows) >= max_rows:
                    break
    except OSError:
        return frozenset()
    tokens = set(csv_scope_tokens(rows))
    if family.startswith("explorer_"):
        for header_name in header:
            normalized_header = " ".join(header_name.strip().lower().split())
            if normalized_header not in {"from", "to", "addr", "address", "owner", "wallet"}:
                continue
            values = {row.get(header_name, "").strip() for row in rows if row.get(header_name, "").strip()}
            if len(values) != 1:
                continue
            tokens.update(token_from_header_value(header_name, next(iter(values))))
    return frozenset(tokens)


def detect_date_span_from_csv(path: Path) -> tuple[str, str, str, int, str, str, str, str]:
    (
        _header,
        _header_index,
        date_field,
        min_timestamp,
        max_timestamp,
        row_count,
        resolution,
        timezone_mode,
        timezone_value,
        timezone_conflict,
    ) = analyze_csv(path)
    return date_field, min_timestamp, max_timestamp, row_count, resolution, timezone_mode, timezone_value, timezone_conflict


def inspect_file(path: Path) -> dict[str, str]:
    suffix = path.suffix.lower()
    header_preview = ""
    family = "binary_evidence"
    data_rows = ""
    date_field = ""
    min_timestamp = ""
    max_timestamp = ""
    timestamp_resolution = ""
    timezone_mode = ""
    timezone_value = ""
    timezone_conflict = ""
    export_timestamp = ""
    report_period_start = ""
    report_period_end = ""
    workbook_sheet_names = ""
    workbook_created_at = ""
    workbook_modified_at = ""
    artifact_kind = ""
    artifact_reason = ""
    archive_summary: dict[str, str] = {}
    path_scope_tokens = extract_scope_tokens(str(path))
    content_scope_tokens: set[str] = set()
    if suffix == ".csv":
        (
            header,
            _header_index,
            date_field,
            min_timestamp,
            max_timestamp,
            row_count,
            timestamp_resolution,
            timezone_mode,
            timezone_value,
            timezone_conflict,
        ) = analyze_csv(path)
        header_preview = " | ".join(header[:8])
        family = classify_file_family(path, header)
        data_rows = str(row_count)
        content_scope_tokens.update(inspect_csv_scope_tokens(path))
    elif suffix == ".pdf":
        family = classify_file_family(path, ())
    elif suffix == ".json":
        family, header_preview = inspect_json_payload(path)
        content_scope_tokens.update(inspect_json_scope_tokens(path))
    elif suffix == ".xlsx":
        workbook = inspect_workbook(path)
        if workbook is not None:
            workbook_row = workbook.to_row()
            family = workbook_row.get("family", family)
            header_preview = workbook_row.get("header_preview", "")
            data_rows = workbook_row.get("data_rows", "")
            date_field = workbook_row.get("date_field", "")
            min_timestamp = workbook_row.get("min_timestamp", "")
            max_timestamp = workbook_row.get("max_timestamp", "")
            timestamp_resolution = workbook_row.get("timestamp_resolution", "")
            timezone_mode = workbook_row.get("timezone_mode", "")
            timezone_value = workbook_row.get("timezone_value", "")
            timezone_conflict = workbook_row.get("timezone_conflict", "")
            export_timestamp = workbook_row.get("export_timestamp", "")
            workbook_sheet_names = workbook_row.get("workbook_sheet_names", "")
            workbook_created_at = workbook_row.get("workbook_created_at", "")
            workbook_modified_at = workbook_row.get("workbook_modified_at", "")
            content_scope_tokens.update(filter(None, workbook_row.get("content_scope_tokens", "").split(";")))
    elif suffix == ".html":
        html = inspect_html(path)
        if html is not None:
            html_row = html.to_row()
            family = html_row.get("family", family)
            header_preview = html_row.get("header_preview", "")
            export_timestamp = html_row.get("export_timestamp", "")
            report_period_start = html_row.get("report_period_start", "")
            report_period_end = html_row.get("report_period_end", "")
    elif suffix in {".zip", ".tar"} or path.name.lower().endswith((".tar.gz", ".tgz")):
        family, header_preview, archive_summary = inspect_archive_payload(path)
        content_scope_tokens.update(extract_scope_tokens(archive_summary.get("archive_scope_tokens", "")))
    artifact = detect_artifact(path, {"family": family, "header_preview": header_preview})
    if artifact is not None:
        artifact_kind = artifact.artifact_kind
        artifact_reason = artifact.reason
    scope_tokens = content_scope_tokens or path_scope_tokens
    return {
        "filename": path.name,
        "suffix": suffix,
        "family": family,
        "header_preview": header_preview,
        "data_rows": data_rows,
        "date_field": date_field,
        "min_timestamp": min_timestamp,
        "max_timestamp": max_timestamp,
        "timestamp_resolution": timestamp_resolution,
        "timezone_mode": timezone_mode,
        "timezone_value": timezone_value,
        "timezone_conflict": timezone_conflict,
        "export_timestamp": export_timestamp,
        "report_period_start": report_period_start,
        "report_period_end": report_period_end,
        "workbook_sheet_names": workbook_sheet_names,
        "workbook_created_at": workbook_created_at,
        "workbook_modified_at": workbook_modified_at,
        "artifact_kind": artifact_kind,
        "artifact_reason": artifact_reason,
        "path_scope_tokens": ";".join(sorted(path_scope_tokens)),
        "content_scope_tokens": ";".join(sorted(content_scope_tokens)),
        "scope_tokens": ";".join(sorted(scope_tokens)),
        "scope_preview": describe_scope_tokens(scope_tokens),
        **archive_summary,
    }


def build_file_inventory(raw_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(file for file in raw_dir.rglob("*") if file.is_file()):
        row = inspect_file(path)
        relative = str(path.relative_to(raw_dir))
        parts = path.relative_to(raw_dir).parts
        row["filename"] = relative
        row["source_path"] = relative
        row["bundle_id"] = parts[0] if len(parts) > 1 else ""
        row["bundle_type"] = "bundle" if len(parts) > 1 else "root_file"
        row["bundle_relative_path"] = str(Path(*parts[1:])) if len(parts) > 1 else path.name
        row["alias_group"] = ""
        row["collision_status"] = ""
        rows.append(row)
    return rows


def _explicit_date_matches(text: str) -> list[tuple[datetime, str]]:
    matches: list[tuple[datetime, str]] = []
    for pattern in EXPORT_DATE_PATTERNS:
        for match in pattern.finditer(text):
            date_text = match.group("date")
            try:
                if "." in date_text:
                    parsed = datetime.strptime(date_text, "%Y.%m.%d")
                elif "-" in date_text:
                    parsed = datetime.strptime(date_text, "%Y-%m-%d")
                else:
                    parsed = datetime.strptime(date_text, "%Y%m%d")
            except ValueError:
                continue
            matches.append((parsed, date_text))
    for match in DAY_MONTH_YEAR_PATTERN.finditer(text):
        first = int(match.group("first"))
        second = int(match.group("second"))
        year = int(match.group("year"))
        if first <= 12 < second:
            parsed = datetime(year, first, second)
        elif second <= 12 < first:
            parsed = datetime(year, second, first)
        else:
            continue
        matches.append((parsed, match.group(0)))
    return matches


def _compact_timestamp_matches(text: str) -> list[tuple[datetime, str]]:
    matches: list[tuple[datetime, str]] = []
    for match in COMPACT_TIMESTAMP_PATTERN.finditer(text):
        value = match.group("timestamp")
        fmt = "%Y%m%d%H%M%S" if len(value) == 14 else "%Y%m%d%H%M"
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        matches.append((parsed, value))
    return matches


def infer_historical_date(
    parts: Iterable[str],
    inspection_row: dict[str, str],
    *,
    policy: HistoricalDatePolicy | None = None,
) -> HistoricalDateDecision:
    effective_policy = policy or HistoricalDatePolicy()
    texts = [part for part in parts if part]

    explicit_matches: list[tuple[datetime, str]] = []
    for text in texts:
        explicit_matches.extend(_explicit_date_matches(text))
    if explicit_matches:
        parsed, date_text = explicit_matches[-1] if effective_policy.prefer_last_explicit else explicit_matches[0]
        return HistoricalDateDecision(
            capture_id=parsed.strftime("%Y-%m"),
            granularity="month",
            basis=f"filename_or_folder:{date_text}",
        )

    if effective_policy.allow_compact_timestamp:
        compact_matches: list[tuple[datetime, str]] = []
        for text in texts:
            compact_matches.extend(_compact_timestamp_matches(text))
        if compact_matches:
            parsed, token = compact_matches[-1] if effective_policy.prefer_last_explicit else compact_matches[0]
            return HistoricalDateDecision(
                capture_id=parsed.strftime("%Y-%m"),
                granularity="month",
                basis=f"filename_or_folder:{token}",
            )

    if effective_policy.allow_year_month_context:
        year_month_matches: list[str] = []
        for text in texts:
            year_month_matches.extend(match.group(0) for match in YEAR_MONTH_PATTERN.finditer(text))
        if year_month_matches:
            token = year_month_matches[-1] if effective_policy.prefer_last_explicit else year_month_matches[0]
            match = YEAR_MONTH_PATTERN.search(token)
            assert match is not None
            return HistoricalDateDecision(
                capture_id=f"{match.group('year')}-{match.group('month')}",
                granularity="month",
                basis=f"filename_or_folder:{token}",
            )

    export_timestamp = inspection_row.get("export_timestamp", "")
    if export_timestamp:
        try:
            parsed = datetime.strptime(export_timestamp, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            parsed = None
        if parsed is not None:
            return HistoricalDateDecision(
                capture_id=parsed.strftime("%Y-%m"),
                granularity="month",
                basis=f"export_timestamp:{export_timestamp}",
            )

    min_timestamp = inspection_row.get("min_timestamp", "")
    if effective_policy.allow_content_span and min_timestamp:
        parsed = datetime.strptime(min_timestamp, "%Y-%m-%d %H:%M:%S")
        return HistoricalDateDecision(
            capture_id=parsed.strftime("%Y-%m"),
            granularity="month",
            basis=f"content_span:{inspection_row.get('min_timestamp', '')}",
        )

    if effective_policy.allow_year_context:
        year_matches: list[str] = []
        for text in texts:
            year_matches.extend(match.group("year") for match in YEAR_PATTERN.finditer(text))
        if year_matches:
            year = year_matches[-1] if effective_policy.prefer_last_explicit else year_matches[0]
            return HistoricalDateDecision(
                capture_id=year,
                granularity="year",
                basis=f"filename_or_folder:{year}",
            )

    return HistoricalDateDecision(
        capture_id="review-required",
        granularity="unknown",
        basis="no_defensible_historical_date",
        review_required=True,
    )
