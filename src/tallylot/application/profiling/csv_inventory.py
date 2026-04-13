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

from .date_inference import (
    filename_anchored_date_only_format,
    infer_date_only_format as infer_profile_date_only_format,
    is_iso_date_only,
)

_HEADER_SCAN_LIMIT = 25
_HEADER_KEYWORDS = (
    "account",
    "amount",
    "asset",
    "balance",
    "chain",
    "currency",
    "date",
    "fee",
    "hash",
    "id",
    "note",
    "order",
    "pair",
    "portfolio",
    "price",
    "quantity",
    "settlement",
    "side",
    "status",
    "subtotal",
    "time",
    "timestamp",
    "token",
    "total",
    "transaction",
    "type",
    "value",
)


def inventory_csv_content(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        delimiter = _sniff_csv_delimiter(handle)
        rows = list(csv.reader(handle, delimiter=delimiter))

    header_index = _header_row_index(rows)
    if header_index is None:
        return (), []

    header = tuple(cell.strip() for cell in rows[header_index])
    content_rows = [
        _row_dict(header, row)
        for row in rows[header_index + 1 :]
        if any(cell.strip() for cell in row)
    ]
    filtered_rows = [row for row in content_rows if not is_placeholder_no_data_row(row)]
    return header, filtered_rows


def is_timestamp_field(name: str) -> bool:
    normalized = re.sub(r"[^a-z]", "", name.lower())
    return normalized in {
        "timestamp",
        "timestamputc",
        "date",
        "datetime",
        "datetimeutc",
        "time",
        "transactiondate",
    }


def timestamp_resolution(value: str) -> str:
    if not value:
        return ""
    text = value.strip()
    if len(text) == 10 and text.count("-") == 2:
        return "date_only"
    if ":" in text:
        return "second"
    return "unknown"


def infer_date_only_format(
    values: list[str],
    *,
    filename: str = "",
) -> str | None:
    return infer_profile_date_only_format(values, filename=filename)


def value_has_non_utc_offset(value: str) -> bool:
    stripped = value.strip()
    return len(stripped) >= 6 and stripped[-6] in {"+", "-"} and stripped[-3] == ":"


def filename_timezone(filename: str) -> timezone | None:
    match = re.search(
        r"\(UTC(?P<sign>[+-]{1,2})(?P<hours>\d{1,2})(?::(?P<minutes>\d{2}))?\)",
        filename,
    )
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


def parse_inventory_timestamp(
    value: str,
    *,
    source_timezone: timezone | None,
    filename: str = "",
    date_only_format: str | None = None,
) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    exact_match = _exact_inventory_timestamp(
        text, filename=filename, date_only_format=date_only_format
    )
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
    for index, row in enumerate(rows[:_HEADER_SCAN_LIMIT]):
        if _is_plausible_header_row(row):
            return index
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
    return {
        key: value.strip()
        for key, value in zip_longest(header, row, fillvalue="")
        if key
    }


def _row_values(row: Mapping[str, str | list[str]]) -> list[str]:
    values: list[str] = []
    for value in row.values():
        if isinstance(value, list):
            values.extend(str(item).strip() for item in value)
            continue
        values.append(str(value).strip())
    return values


def _exact_inventory_timestamp(
    text: str,
    *,
    filename: str = "",
    date_only_format: str | None = None,
) -> datetime | None:
    parsed: datetime | None = None
    if text.endswith(" UTC"):
        parsed = _try_datetime(text, "%Y-%m-%d %H:%M:%S UTC", tzinfo=UTC)
    elif text.endswith("Z"):
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
            parsed = _try_datetime(text, fmt, tzinfo=UTC)
            if parsed is not None:
                break
    elif value_has_non_utc_offset(text):
        try:
            parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S%z").astimezone(UTC)
        except ValueError:
            parsed = None
    elif is_iso_date_only(text):
        parsed = _try_datetime(text, "%Y-%m-%d", tzinfo=UTC)
    elif date_only_format is not None:
        parsed = _try_datetime(text, date_only_format, tzinfo=UTC)
    else:
        anchored_format = filename_anchored_date_only_format(text, filename=filename)
        if anchored_format is not None:
            parsed = _try_datetime(text, anchored_format, tzinfo=UTC)
    return parsed


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


def _is_plausible_header_row(row: list[str]) -> bool:
    non_empty = [cell.strip() for cell in row if cell.strip()]
    if len(non_empty) < 2:
        return False
    keyword_hits = sum(1 for cell in non_empty if _has_header_keyword(cell))
    if len(non_empty) <= 3 and keyword_hits < 2:
        return False
    payload_like_count = sum(1 for cell in non_empty if _is_payload_like_cell(cell))
    if payload_like_count * 2 > len(non_empty):
        return False
    header_like_count = sum(1 for cell in non_empty if _is_header_like_cell(cell))
    return header_like_count * 2 >= len(non_empty) or keyword_hits >= 2


def _has_header_keyword(value: str) -> bool:
    normalized = _normalized_header_text(value)
    return any(keyword in normalized.split() for keyword in _HEADER_KEYWORDS)


def _is_header_like_cell(value: str) -> bool:
    text = value.strip()
    if not text or _is_payload_like_cell(text):
        return False
    normalized = _normalized_header_text(text)
    return bool(normalized and re.search(r"[a-z]", normalized))


def _normalized_header_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _is_payload_like_cell(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    if _exact_inventory_timestamp(text) is not None:
        return True
    if re.fullmatch(r"[A-Z]{2,10}", text):
        return True
    return bool(
        re.fullmatch(
            r"[$€£]?\d[\d,]*(?:\.\d+)?%?"
            r"|[$€£]?\d[\d,]*(?:\.\d+)?/[A-Za-z]+"
            r"|[+-]?\d+(?:\.\d+)?",
            text,
        )
    )
