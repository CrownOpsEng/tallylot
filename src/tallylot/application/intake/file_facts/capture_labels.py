"""Capture-label inference for intake files."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from .inspection import parse_timestamp
from .models import IntakeFileFacts

PATH_DATE_PATTERNS = (
    re.compile(
        r"(?<!\d)(?P<year>20\d{2})[-_.](?P<month>\d{2})[-_.](?P<day>\d{2})(?!\d)"
    ),
    re.compile(
        r"(?<!\d)(?P<month>\d{2})[-_.](?P<day>\d{2})[-_.](?P<year>20\d{2})(?!\d)"
    ),
    re.compile(
        r"(?<!\d)(?P<year>20\d{2})(?P<month>\d{2})(?P<day>\d{2})(?:\d{4})?(?!\d)"
    ),
)
PATH_MONTH_PATTERNS = (
    re.compile(r"(?<!\d)(?P<year>20\d{2})[-_/](?P<month>\d{2})(?!\d)"),
    re.compile(r"(?<!\d)(?P<year>20\d{2})(?P<month>\d{2})(?!\d)"),
)
PATH_YEAR_PATTERN = re.compile(r"(?<!\d)(20\d{2})(?!\d)")


def detect_capture_label(relative_path: str, facts: IntakeFileFacts) -> str:
    if facts.min_timestamp:
        parsed = parse_timestamp(facts.min_timestamp)
        if parsed is not None:
            return parsed.strftime("%Y-%m")
    return _capture_label_from_path(relative_path)


def _capture_label_from_path(relative_path: str) -> str:
    parsed_dates = sorted(_parsed_path_dates(relative_path))
    if parsed_dates:
        return parsed_dates[-1].strftime("%Y-%m")
    for pattern in PATH_MONTH_PATTERNS:
        match = pattern.search(relative_path)
        if match is not None:
            return f"{match.group('year')}-{match.group('month')}"
    year_match = PATH_YEAR_PATTERN.search(relative_path)
    if year_match is not None:
        return year_match.group(1)
    return ""


def _parsed_path_dates(relative_path: str) -> list[datetime]:
    parsed_dates: list[datetime] = []
    for pattern in PATH_DATE_PATTERNS:
        for match in pattern.finditer(relative_path):
            month = int(match.group("month"))
            day = int(match.group("day"))
            year = int(match.group("year"))
            try:
                parsed_dates.append(datetime(year, month, day, tzinfo=UTC))
            except ValueError:
                continue
    return parsed_dates
