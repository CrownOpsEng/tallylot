"""CSV inspection and signal extraction for intake files."""

from __future__ import annotations

import csv
import re
from datetime import UTC, datetime
from itertools import zip_longest
from pathlib import Path

from tallylot.domain.location_identifiers import (
    BTC_ADDRESS_PATTERN,
    CARDANO_ACCOUNT_KEY_PATTERN,
    EVM_ADDRESS_PATTERN,
    TRON_ADDRESS_PATTERN,
    scope_token_for_identifier,
)

from .models import IntakeFileFacts

_HEADER_SCAN_LIMIT = 25
_HEADER_KEYWORDS = (
    "account",
    "amount",
    "asset",
    "balance",
    "chain",
    "coin",
    "currency",
    "date",
    "fee",
    "hash",
    "id",
    "name",
    "network",
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
    "wallet",
)

TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S UTC",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%SZ",
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
        scope_tokens = _scope_tokens(relative_path, [], [])
        return IntakeFileFacts(
            scope_tokens=tuple(sorted(scope_tokens)),
            routing_scope_tokens=_routing_scope_tokens(relative_path, [], []),
            network_hints=_network_hints(relative_path, (), [], []),
        )

    header, rows, title_rows = _read_csv_rows(path)
    timestamp_values = _timestamp_values(rows, header)
    scope_tokens = _scope_tokens(relative_path, rows, title_rows)
    network_hints = _network_hints(relative_path, header, rows, title_rows)
    return IntakeFileFacts(
        header=header,
        min_timestamp=timestamp_values[0] if timestamp_values else "",
        max_timestamp=timestamp_values[-1] if timestamp_values else "",
        observed_period_start=_observed_period_start(timestamp_values),
        observed_period_end=_observed_period_end(timestamp_values),
        observed_period_label=_observed_period_label(timestamp_values),
        scope_tokens=tuple(sorted(scope_tokens)),
        routing_scope_tokens=_routing_scope_tokens(relative_path, rows, title_rows),
        network_hints=network_hints,
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


def _timestamp_values(
    rows: list[dict[str, str]],
    header: tuple[str, ...],
) -> list[str]:
    field_name = next((name for name in TIMESTAMP_FIELD_NAMES if name in header), "")
    if not field_name:
        lowered = {name.lower(): name for name in header}
        field_name = next(
            (
                lowered[name.lower()]
                for name in TIMESTAMP_FIELD_NAMES
                if name.lower() in lowered
            ),
            "",
        )
    if not field_name:
        return []
    parsed_values = [
        parsed
        for row in rows
        if (parsed := parse_timestamp(_cell_text(row.get(field_name)))) is not None
    ]
    return [value.strftime("%Y-%m-%d %H:%M:%S") for value in sorted(parsed_values)]


def _observed_period_start(timestamp_values: list[str]) -> str:
    if not timestamp_values:
        return ""
    return timestamp_values[0][:10]


def _observed_period_end(timestamp_values: list[str]) -> str:
    if not timestamp_values:
        return ""
    return timestamp_values[-1][:10]


def _observed_period_label(timestamp_values: list[str]) -> str:
    if not timestamp_values:
        return ""
    start = timestamp_values[0][:7]
    end = timestamp_values[-1][:7]
    return start if start == end else f"{start}..{end}"


def _read_csv_rows(
    path: Path,
) -> tuple[tuple[str, ...], list[dict[str, str]], list[list[str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        rows = list(csv.reader(handle, dialect=dialect))
    header_index = _header_row_index(rows)
    if header_index is None:
        return (), [], []
    header = tuple(cell.strip() for cell in rows[header_index])
    title_rows = rows[:header_index]
    content_rows = [
        _row_dict(header, row)
        for row in rows[header_index + 1 :]
        if any(cell.strip() for cell in row)
    ]
    return header, content_rows, title_rows


def _scope_tokens(
    relative_path: str,
    rows: list[dict[str, str]],
    title_rows: list[list[str]],
) -> set[str]:
    tokens: set[str] = set()
    lower_path = relative_path.lower()
    for token in _identifier_scope_tokens(relative_path):
        tokens.add(token)
    for match in ACCOUNT_SEGMENT_PATTERN.finditer(lower_path):
        tokens.add(
            f"label:{match.group(0).lower().replace(' ', '-').replace('_', '-')}"
        )
    for row in rows[:50]:
        for value in row.values():
            for token in _identifier_scope_tokens(value):
                tokens.add(token)
    for title_row in title_rows[:50]:
        title_text = " ".join(cell.strip() for cell in title_row)
        for token in _identifier_scope_tokens(title_text):
            tokens.add(token)
        for match in ACCOUNT_SEGMENT_PATTERN.finditer(title_text.lower()):
            tokens.add(
                f"label:{match.group(0).lower().replace(' ', '-').replace('_', '-')}"
            )
    return tokens


def _network_hints(
    relative_path: str,
    header: tuple[str, ...],
    rows: list[dict[str, str]],
    title_rows: list[list[str]],
) -> tuple[str, ...]:
    row_text = " ".join(
        _cell_text(value) for row in rows[:50] for value in row.values()
    )
    title_text = " ".join(
        _cell_text(cell) for title_row in title_rows[:50] for cell in title_row
    )
    search_text = " ".join((relative_path, *header, row_text, title_text)).lower()
    ordered_matches: list[tuple[int, str]] = []
    for token, network in NETWORK_HINTS:
        position = search_text.find(token)
        if position != -1:
            ordered_matches.append((position, network))
    hints: list[str] = []
    seen: set[str] = set()
    for _, network in sorted(ordered_matches, key=lambda item: (item[0], item[1])):
        if network in seen:
            continue
        seen.add(network)
        hints.append(network)
    return tuple(hints)


def _routing_scope_tokens(
    relative_path: str,
    rows: list[dict[str, str]],
    title_rows: list[list[str]],
) -> tuple[str, ...]:
    path_tokens = _identifier_scope_tokens(relative_path)
    title_tokens = _title_identifier_scope_tokens(title_rows)
    row_token_sets = _row_identifier_scope_token_sets(rows)
    selected_tokens: set[str] = set()
    if not row_token_sets:
        selected_tokens = _single_identifier(path_tokens) or _single_identifier(
            title_tokens
        )
    else:
        row_identifiers: set[str] = set()
        for row_tokens in row_token_sets:
            row_identifiers.update(row_tokens)
        common_tokens = set(row_token_sets[0])
        for row_tokens in row_token_sets[1:]:
            common_tokens.intersection_update(row_tokens)
        selected_tokens = _select_routing_tokens(
            common_tokens, path_tokens=path_tokens, title_tokens=title_tokens
        )
        if not selected_tokens:
            selected_tokens = _single_identifier(path_tokens & row_identifiers)
        if not selected_tokens:
            selected_tokens = _single_identifier(title_tokens & row_identifiers)
    return tuple(sorted(selected_tokens))


def _single_identifier(tokens: set[str]) -> set[str]:
    if len(tokens) == 1:
        return set(tokens)
    return set()


def _select_routing_tokens(
    common_tokens: set[str],
    *,
    path_tokens: set[str],
    title_tokens: set[str],
) -> set[str]:
    if not common_tokens:
        return set()
    if len(common_tokens) == 1:
        return common_tokens
    path_common = path_tokens & common_tokens
    if len(path_common) == 1:
        return path_common
    title_common = title_tokens & common_tokens
    if len(title_common) == 1:
        return title_common
    return set()


def _title_identifier_scope_tokens(title_rows: list[list[str]]) -> set[str]:
    tokens: set[str] = set()
    for title_row in title_rows[:50]:
        title_text = " ".join(cell.strip() for cell in title_row)
        tokens.update(_identifier_scope_tokens(title_text))
    return tokens


def _row_identifier_scope_token_sets(rows: list[dict[str, str]]) -> list[set[str]]:
    token_sets: list[set[str]] = []
    for row in rows[:50]:
        row_tokens = {
            token for value in row.values() for token in _identifier_scope_tokens(value)
        }
        if row_tokens:
            token_sets.append(row_tokens)
    return token_sets


def _row_dict(header: tuple[str, ...], row: list[str]) -> dict[str, str]:
    return {
        key: value.strip()
        for key, value in zip_longest(header, row, fillvalue="")
        if key
    }


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
    if parse_timestamp(text) is not None:
        return True
    return bool(
        re.fullmatch(
            r"[$€£]?\d[\d,]*(?:\.\d+)?%?"
            r"|[$€£]?\d[\d,]*(?:\.\d+)?/[A-Za-z]+"
            r"|[+-]?\d+(?:\.\d+)?",
            text,
        )
    )


def _cell_text(value: str | None) -> str:
    if value is None:
        return ""
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
