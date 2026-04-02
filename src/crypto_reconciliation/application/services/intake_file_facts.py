"""Typed file facts used by intake routing and review decisions."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

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
EVM_ADDRESS_PATTERN = re.compile(r"0x[a-fA-F0-9]{40}")
ACCOUNT_SEGMENT_PATTERN = re.compile(r"account[-_ ]?[a-z0-9]+", re.IGNORECASE)


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
            network_hints=tuple(sorted(_network_hints(relative_path, ()))),
        )

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = tuple(reader.fieldnames or ())
        rows = list(reader)
    timestamp_values = _timestamp_values(rows, header)
    scope_tokens = _scope_tokens(relative_path, rows)
    network_hints = _network_hints(relative_path, header)
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
    path_match = re.search(r"(?P<year>20\d{2})[-_/]?(?P<month>\d{2})", relative_path)
    if path_match is not None:
        return f"{path_match.group('year')}-{path_match.group('month')}"
    return ""


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
    for match in EVM_ADDRESS_PATTERN.finditer(relative_path):
        tokens.add(f"evm:{match.group(0).lower()}")
    for match in ACCOUNT_SEGMENT_PATTERN.finditer(lower_path):
        tokens.add(f"label:{match.group(0).lower().replace(' ', '-').replace('_', '-')}")
    for row in rows[:50]:
        for value in row.values():
            candidates = value if isinstance(value, list) else (value or "",)
            for candidate in candidates:
                for match in EVM_ADDRESS_PATTERN.finditer(candidate):
                    tokens.add(f"evm:{match.group(0).lower()}")
    return tokens


def _network_hints(relative_path: str, header: tuple[str, ...]) -> set[str]:
    search_text = " ".join((relative_path, *header)).lower()
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
