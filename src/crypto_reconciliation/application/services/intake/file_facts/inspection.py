"""CSV inspection and signal extraction for intake files."""

from __future__ import annotations

import csv
import re
from datetime import UTC, datetime
from pathlib import Path

from crypto_reconciliation.domain.wallet_identifiers import (
    BTC_ADDRESS_PATTERN,
    CARDANO_ACCOUNT_KEY_PATTERN,
    EVM_ADDRESS_PATTERN,
    TRON_ADDRESS_PATTERN,
    scope_token_for_identifier,
)

from .models import IntakeFileFacts

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


def parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def _timestamp_values(rows: list[dict[str, CsvCell]], header: tuple[str, ...]) -> list[str]:
    field_name = next((name for name in TIMESTAMP_FIELD_NAMES if name in header), "")
    if not field_name:
        lowered = {name.lower(): name for name in header}
        field_name = next((lowered[name.lower()] for name in TIMESTAMP_FIELD_NAMES if name.lower() in lowered), "")
    if not field_name:
        return []
    parsed_values = [parsed for row in rows if (parsed := parse_timestamp(_cell_text(row.get(field_name)))) is not None]
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
