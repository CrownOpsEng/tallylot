"""Typed file facts used by intake routing and review decisions."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from crypto_reconciliation.domain.wallet_identifiers import (
    BTC_ADDRESS_PATTERN,
    CARDANO_ACCOUNT_KEY_PATTERN,
    EVM_ADDRESS_PATTERN,
    TRON_ADDRESS_PATTERN,
    scope_token_for_identifier,
)

type CsvCell = str | list[str]

TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S UTC",
    "%Y-%m-%d",
)
TIMESTAMP_FIELD_NAMES = (
    "Timestamp",
    "Date",
    "DateTime (UTC)",
    "Time",
)
NETWORK_HINTS = (
    ("polygon", "polygon"),
    ("matic", "polygon"),
    ("bsc", "bsc"),
    ("binance smart chain", "bsc"),
    ("arb", "arbitrum"),
    ("arbitrum", "arbitrum"),
    ("eth", "ethereum"),
    ("ethereum", "ethereum"),
    ("near", "near"),
    ("bitcoin", "bitcoin"),
    ("btc", "bitcoin"),
    ("cardano", "cardano"),
    ("ada", "cardano"),
    ("tron", "tron"),
    ("trx", "tron"),
    ("sol", "solana"),
    ("solana", "solana"),
)
ACCOUNT_SEGMENT_PATTERN = re.compile(r"account[-_ ]?[a-z0-9]+", re.IGNORECASE)
PATH_DATE_PATTERNS = (
    re.compile(r"(?<!\d)(?P<year>20\d{2})[-_.](?P<month>\d{2})[-_.](?P<day>\d{2})(?!\d)"),
    re.compile(r"(?<!\d)(?P<month>\d{2})[-_.](?P<day>\d{2})[-_.](?P<year>20\d{2})(?!\d)"),
    re.compile(r"(?<!\d)(?P<year>20\d{2})(?P<month>\d{2})(?P<day>\d{2})(?:\d{4})?(?!\d)"),
)
PATH_MONTH_PATTERNS = (
    re.compile(r"(?<!\d)(?P<year>20\d{2})[-_/](?P<month>\d{2})(?!\d)"),
    re.compile(r"(?<!\d)(?P<year>20\d{2})(?P<month>\d{2})(?!\d)"),
)
PATH_YEAR_PATTERN = re.compile(r"(?<!\d)(20\d{2})(?!\d)")


@dataclass(frozen=True)
class IntakeFileFacts:
    header: tuple[str, ...] = ()
    min_timestamp: str = ""
    max_timestamp: str = ""
    scope_tokens: tuple[str, ...] = ()
    network_hints: tuple[str, ...] = ()


def inspect_intake_file(path: Path, *, relative_path: str) -> IntakeFileFacts:
    if path.suffix.lower() != ".csv":
        return IntakeFileFacts(
            scope_tokens=tuple(sorted(_scope_tokens(relative_path, []))),
            network_hints=tuple(sorted(_network_hints(relative_path, (), []))),
        )

    header, rows = _read_csv_rows(path)
    timestamp_values = _timestamp_values(rows, header)
    scope_tokens = _scope_tokens(relative_path, rows)
    network_hints = _network_hints(relative_path, header, rows)
    return IntakeFileFacts(
        header=header,
        min_timestamp=timestamp_values[0] if timestamp_values else "",
        max_timestamp=timestamp_values[-1] if timestamp_values else "",
        scope_tokens=tuple(sorted(scope_tokens)),
        network_hints=tuple(sorted(network_hints)),
    )


def detect_capture_id(relative_path: str, facts: IntakeFileFacts) -> str:
    if facts.min_timestamp:
        parsed = _parse_timestamp(facts.min_timestamp)
        if parsed is not None:
            return parsed.strftime("%Y-%m")
    return _capture_id_from_path(relative_path)


def _timestamp_values(rows: list[dict[str, CsvCell]], header: tuple[str, ...]) -> list[str]:
    field_name = next((name for name in TIMESTAMP_FIELD_NAMES if name in header), "")
    if not field_name:
        lowered = {name.lower(): name for name in header}
        field_name = next((lowered[name.lower()] for name in TIMESTAMP_FIELD_NAMES if name.lower() in lowered), "")
    if not field_name:
        return []
    parsed_values = [
        parsed for row in rows if (parsed := _parse_timestamp(_cell_text(row.get(field_name)))) is not None
    ]
    return [value.strftime("%Y-%m-%d %H:%M:%S") for value in sorted(parsed_values)]


def _read_csv_rows(path: Path) -> tuple[tuple[str, ...], list[dict[str, CsvCell]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(handle, dialect=dialect)
        return tuple(reader.fieldnames or ()), list(reader)


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def _scope_tokens(relative_path: str, rows: list[dict[str, CsvCell]]) -> set[str]:
    tokens: set[str] = set()
    lower_path = relative_path.lower()
    for token in _identifier_scope_tokens(relative_path):
        tokens.add(token)
    for match in ACCOUNT_SEGMENT_PATTERN.finditer(lower_path):
        tokens.add(f"label:{match.group(0).lower().replace(' ', '-').replace('_', '-')}")
    for row in rows[:50]:
        for value in row.values():
            candidates = value if isinstance(value, list) else (value or "",)
            for candidate in candidates:
                for token in _identifier_scope_tokens(candidate):
                    tokens.add(token)
    return tokens


def _network_hints(
    relative_path: str,
    header: tuple[str, ...],
    rows: list[dict[str, CsvCell]],
) -> set[str]:
    row_text = " ".join(_cell_text(value) for row in rows[:50] for value in row.values())
    search_text = " ".join((relative_path, *header, row_text)).lower()
    hints: set[str] = set()
    for token, network in NETWORK_HINTS:
        if token in search_text:
            hints.add(network)
    return hints


def _cell_text(value: CsvCell | None) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(value).strip()
    return value.strip()


def _identifier_scope_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for pattern in (
        EVM_ADDRESS_PATTERN,
        BTC_ADDRESS_PATTERN,
        TRON_ADDRESS_PATTERN,
        CARDANO_ACCOUNT_KEY_PATTERN,
    ):
        for match in pattern.finditer(text):
            token = scope_token_for_identifier(match.group(0))
            if token:
                tokens.add(token)
    return tokens


def _capture_id_from_path(relative_path: str) -> str:
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
            if "month" in match.groupdict() and "day" in match.groupdict() and "year" in match.groupdict():
                month = int(match.group("month"))
                day = int(match.group("day"))
                year = int(match.group("year"))
                try:
                    parsed_dates.append(datetime(year, month, day, tzinfo=UTC))
                except ValueError:
                    continue
    return parsed_dates
