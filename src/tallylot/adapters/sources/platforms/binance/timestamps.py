"""Binance timestamp parsing rules."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

FILENAME_OFFSET_PATTERN = re.compile(r"UTC-(?P<sign>[+-])(?P<hours>\d+)")
INLINE_UTC_PATTERN = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})(?: (?P<time>\d{2}:\d{2}:\d{2}))?\(UTC(?P<offset>[+-]?\d+)\)$"
)


def parse_export_timestamp(value: str, filename: str) -> datetime:
    stripped = value.strip()
    inline_match = INLINE_UTC_PATTERN.fullmatch(stripped)
    if inline_match is not None:
        time_value = inline_match.group("time") or "00:00:00"
        parsed = datetime.strptime(
            f"{inline_match.group('date')} {time_value}",
            "%Y-%m-%d %H:%M:%S",
        ).replace(tzinfo=UTC)
        hours = int(inline_match.group("offset"))
        return (parsed - timedelta(hours=hours)).replace(tzinfo=None)
    parsed = datetime.strptime(stripped, "%y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    return _apply_filename_offset(parsed, filename).replace(tzinfo=None)


def parse_transaction_history_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%y-%m-%d %H:%M:%S").replace(tzinfo=UTC).replace(tzinfo=None)


def _apply_filename_offset(parsed: datetime, filename: str) -> datetime:
    match = FILENAME_OFFSET_PATTERN.search(filename)
    if match is None:
        return parsed
    hours = int(match.group("hours"))
    direction = 1 if match.group("sign") == "-" else -1
    return parsed + timedelta(hours=hours * direction)
