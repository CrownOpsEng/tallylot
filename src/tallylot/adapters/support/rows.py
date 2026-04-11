"""Shared CSV traversal and grouped-row support for adapters."""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from collections.abc import Callable, Collection, Hashable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from itertools import zip_longest
from typing import TypeVar

from tallylot.domain.issues import IssueRecord
from tallylot.ports.source_profiles import SourceProfile, parse_family_claim_tokens

from .drafts import EconomicActivityDraft

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

type CsvRowParseResult = EconomicActivityDraft | IssueRecord | None
type CsvRowParser = Callable[["CsvRowContext"], CsvRowParseResult]

GroupKeyT = TypeVar("GroupKeyT", bound=Hashable)


@dataclass(frozen=True)
class CsvRowContext:
    path: Path
    row_index: int
    row: dict[str, str]

    @property
    def raw_file(self) -> str:
        return self.path.name

    @property
    def raw_row_ref(self) -> str:
        return f"row:{self.row_index}"


def matching_file_paths(raw_dir: Path, *, pattern: str = "*.csv") -> tuple[Path, ...]:
    return tuple(sorted(raw_dir.rglob(pattern)))


def skip_files_outside_profile_families(
    raw_dir: Path,
    profile: SourceProfile,
    *,
    adapter_id: str | None = None,
    family_ids: Collection[str] = (),
    extra_skip: Callable[[Path], bool] | None = None,
) -> Callable[[Path], bool]:
    inventory_by_path = {entry.relative_path: entry for entry in profile.file_inventory}
    adapter_key = str(profile.adapter_id) if adapter_id is None else adapter_id
    allowed_families = frozenset(family_ids)

    def skip_file(path: Path) -> bool:
        if extra_skip is not None and extra_skip(path):
            return True
        relative_path = path.relative_to(raw_dir).as_posix()
        entry = inventory_by_path.get(relative_path)
        if entry is None:
            return True
        claimed_families = {
            family_id
            for claim_adapter_id, family_id in parse_family_claim_tokens(entry.family)
            if claim_adapter_id == adapter_key
        }
        if not claimed_families:
            return True
        return bool(allowed_families and claimed_families.isdisjoint(allowed_families))

    return skip_file


def read_csv_header(path: Path) -> tuple[str, ...]:
    header, _, _ = _read_csv_table(path)
    return header


def read_csv_rows(path: Path) -> tuple[dict[str, str], ...]:
    _, rows, _ = _read_csv_table(path)
    return tuple(rows)


def iter_csv_row_contexts(
    raw_dir: Path,
    *,
    pattern: str = "*.csv",
    skip_file: Callable[[Path], bool] | None = None,
) -> Iterator[CsvRowContext]:
    for path in matching_file_paths(raw_dir, pattern=pattern):
        if skip_file is not None and skip_file(path):
            continue
        header, rows, header_index = _read_csv_table(path)
        del header
        if header_index is None:
            continue
        for row_index, row in enumerate(rows, start=header_index + 2):
            yield CsvRowContext(path=path, row_index=row_index, row=row)


def collect_csv_row_results(
    raw_dir: Path,
    parse_row: CsvRowParser,
    *,
    pattern: str = "*.csv",
    skip_file: Callable[[Path], bool] | None = None,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    drafts: list[EconomicActivityDraft] = []
    issues: list[IssueRecord] = []
    for row_context in iter_csv_row_contexts(
        raw_dir, pattern=pattern, skip_file=skip_file
    ):
        parsed = parse_row(row_context)
        if isinstance(parsed, IssueRecord):
            issues.append(parsed)
            continue
        if parsed is not None:
            drafts.append(parsed)
    return tuple(drafts), tuple(issues)


def group_csv_row_contexts(
    raw_dir: Path,
    key_for_row: Callable[[CsvRowContext], GroupKeyT | None],
    *,
    pattern: str = "*.csv",
    skip_file: Callable[[Path], bool] | None = None,
) -> dict[GroupKeyT, tuple[CsvRowContext, ...]]:
    grouped: dict[GroupKeyT, list[CsvRowContext]] = defaultdict(list)
    for row_context in iter_csv_row_contexts(
        raw_dir, pattern=pattern, skip_file=skip_file
    ):
        group_key = key_for_row(row_context)
        if group_key is None:
            continue
        grouped[group_key].append(row_context)
    return {group_key: tuple(rows) for group_key, rows in grouped.items()}


def _read_csv_table(
    path: Path,
) -> tuple[tuple[str, ...], list[dict[str, str]], int | None]:
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
        return (), [], None
    header = tuple(cell.strip() for cell in rows[header_index])
    content_rows = [
        _row_dict(header, row)
        for row in rows[header_index + 1 :]
        if any(cell.strip() for cell in row)
    ]
    return header, content_rows, header_index


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
    if _parse_timestamp(text) is not None:
        return True
    return bool(
        re.fullmatch(
            r"[$€£]?\d[\d,]*(?:\.\d+)?%?"
            r"|[$€£]?\d[\d,]*(?:\.\d+)?/[A-Za-z]+"
            r"|[+-]?\d+(?:\.\d+)?",
            text,
        )
    )


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None
