"""CSV inventory parsing and timestamp helpers for profiling workflows."""

from __future__ import annotations

import csv
import re
import time
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta, timezone
from io import TextIOBase
from itertools import zip_longest
from pathlib import Path


def inventory_csv_content(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        delimiter = _sniff_csv_delimiter(handle)
        rows = list(csv.reader(handle, delimiter=delimiter))

    header_index = _header_row_index(rows)
    if header_index is None:
        return (), []

    header = tuple(cell.strip() for cell in rows[header_index])
    content_rows = [_row_dict(header, row) for row in rows[header_index + 1 :] if any(cell.strip() for cell in row)]
    filtered_rows = [row for row in content_rows if not is_placeholder_no_data_row(row)]
    return header, filtered_rows


def is_timestamp_field(name: str) -> bool:
    normalized = re.sub(r"[^a-z]", "", name.lower())
    return normalized in {"timestamp", "timestamputc", "date", "datetime", "datetimeutc", "time", "transactiondate"}


def timestamp_resolution(value: str) -> str:
    if not value:
        return ""
    if len(value.strip()) == 10 and value.count("-") == 2:
        return "date_only"
    if ":" in value:
        return "second"
    return "unknown"


def value_has_non_utc_offset(value: str) -> bool:
    stripped = value.strip()
    return len(stripped) >= 6 and stripped[-6] in {"+", "-"} and stripped[-3] == ":"


def filename_timezone(filename: str) -> timezone | None:
    match = re.search(r"\(UTC(?P<sign>[+-]{1,2})(?P<hours>\d{1,2})(?::(?P<minutes>\d{2}))?\)", filename)
    if match is None:
        return None
    sign_text = match.group("sign")
    sign = -1 if sign_text.startswith(("-", "--")) else 1
    hours = int(match.group("hours"))
    minutes = int(match.group("minutes") or "0")
    return timezone(sign * timedelta(hours=hours, minutes=minutes))


def format_timezone_value(value: timezone) -> str:
    offset = value.utcoffset(None) or timedelta()
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    hours, minutes = divmod(total_minutes, 60)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def parse_inventory_timestamp(value: str, *, source_timezone: timezone | None) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    exact_match = _exact_inventory_timestamp(text)
    if exact_match is not None:
        return exact_match
    for fmt in ("%Y-%m-%d %H:%M:%S", "%y-%m-%d %H:%M:%S"):
        parsed = _timestamp_from_format(text, fmt, source_timezone=source_timezone)
        if parsed is not None:
            return parsed
    return None


def is_placeholder_no_data_row(row: Mapping[str, str | list[str]]) -> bool:
    values = [value.strip() for value in _row_values(row) if value and value.strip()]
    return len(values) == 1 and values[0].lower() == "no data matches the criteria."


def _sniff_csv_delimiter(handle: TextIOBase) -> str:
    sample = handle.read(4096)
    handle.seek(0)
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
    except csv.Error:
        return ","


def _header_row_index(rows: list[list[str]]) -> int | None:
    candidates = [
        (len([cell for cell in row if cell.strip()]), index)
        for index, row in enumerate(rows)
        if len([cell for cell in row if cell.strip()]) >= 2
    ]
    if not candidates:
        return None
    widest = max(width for width, _ in candidates)
    return next(index for width, index in candidates if width == widest)


def _row_dict(header: tuple[str, ...], row: list[str]) -> dict[str, str]:
    return {key: value.strip() for key, value in zip_longest(header, row, fillvalue="") if key}


def _row_values(row: Mapping[str, str | list[str]]) -> list[str]:
    values: list[str] = []
    for value in row.values():
        if isinstance(value, list):
            values.extend(str(item).strip() for item in value)
            continue
        values.append(str(value).strip())
    return values


def _exact_inventory_timestamp(text: str) -> datetime | None:
    if text.endswith(" UTC"):
        return _try_datetime(text, "%Y-%m-%d %H:%M:%S UTC", tzinfo=UTC)
    if text.endswith("Z"):
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
            parsed = _try_datetime(text, fmt, tzinfo=UTC)
            if parsed is not None:
                return parsed
    if value_has_non_utc_offset(text):
        try:
            return datetime.strptime(text, "%Y-%m-%d %H:%M:%S%z").astimezone(UTC)
        except ValueError:
            return None
    if len(text) == 10 and text.count("-") == 2:
        return _try_datetime(text, "%Y-%m-%d", tzinfo=UTC)
    return None


def _try_datetime(
    text: str,
    fmt: str,
    *,
    tzinfo: timezone | None = None,
) -> datetime | None:
    try:
        parsed = datetime.strptime(text, fmt).replace(tzinfo=tzinfo or UTC)
    except ValueError:
        return None
    return parsed


def _timestamp_from_format(
    text: str,
    fmt: str,
    *,
    source_timezone: timezone | None,
) -> datetime | None:
    try:
        parsed = time.strptime(text, fmt)
    except ValueError:
        return None
    return datetime(
        parsed.tm_year,
        parsed.tm_mon,
        parsed.tm_mday,
        parsed.tm_hour,
        parsed.tm_min,
        parsed.tm_sec,
        tzinfo=source_timezone or UTC,
    ).astimezone(UTC)
