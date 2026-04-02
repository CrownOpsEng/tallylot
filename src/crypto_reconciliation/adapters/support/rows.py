"""Shared CSV traversal and grouped-row support for adapters."""

from __future__ import annotations

import csv
from collections import defaultdict
from collections.abc import Callable, Hashable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from crypto_reconciliation.domain.models import IssueRecord

from .drafts import EconomicActivityDraft

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


def read_csv_header(path: Path) -> tuple[str, ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return tuple(reader.fieldnames or ())


def read_csv_rows(path: Path) -> tuple[dict[str, str], ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return tuple(csv.DictReader(handle))


def iter_csv_row_contexts(
    raw_dir: Path,
    *,
    pattern: str = "*.csv",
    skip_file: Callable[[Path], bool] | None = None,
) -> Iterator[CsvRowContext]:
    for path in matching_file_paths(raw_dir, pattern=pattern):
        if skip_file is not None and skip_file(path):
            continue
        for row_index, row in enumerate(read_csv_rows(path), start=2):
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
    for row_context in iter_csv_row_contexts(raw_dir, pattern=pattern, skip_file=skip_file):
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
    for row_context in iter_csv_row_contexts(raw_dir, pattern=pattern, skip_file=skip_file):
        group_key = key_for_row(row_context)
        if group_key is None:
            continue
        grouped[group_key].append(row_context)
    return {group_key: tuple(rows) for group_key, rows in grouped.items()}
