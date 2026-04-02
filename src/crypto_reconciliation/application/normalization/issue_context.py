"""Normalization issue-context enrichment."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

from crypto_reconciliation.domain.issues import IssueRecord
from crypto_reconciliation.domain.value_objects import format_timestamp
from crypto_reconciliation.infrastructure.serialization.csv_inventory import (
    filename_timezone,
    inventory_csv_content,
    parse_inventory_timestamp,
)
from crypto_reconciliation.ports.source_profiles import FileInventoryEntry

_ROW_NUMBER_PATTERN = re.compile(r"(?:^|[^0-9])row:(?P<row>\d+)\b")
_TIMESTAMP_PATTERNS = (
    re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC"),
    re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"),
    re.compile(r"\d{2}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"),
    re.compile(r"\d{4}-\d{2}-\d{2}"),
)


def enrich_issue_context_timestamps(
    issues: tuple[IssueRecord, ...],
    *,
    raw_dir: Path,
    inventory: tuple[FileInventoryEntry, ...],
) -> tuple[IssueRecord, ...]:
    resolver = _IssueTimestampResolver(raw_dir=raw_dir, inventory=inventory)
    enriched: list[IssueRecord] = []
    for issue in issues:
        if issue.context_timestamp:
            enriched.append(issue)
            continue
        context_timestamp = resolver.resolve(issue)
        if not context_timestamp:
            enriched.append(issue)
            continue
        enriched.append(replace(issue, context_timestamp=context_timestamp))
    return tuple(enriched)


class _IssueTimestampResolver:
    def __init__(self, *, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> None:
        self._raw_dir = raw_dir
        self._by_relative_path = {entry.relative_path: entry for entry in inventory if entry.relative_path}
        self._by_name: dict[str, list[FileInventoryEntry]] = defaultdict(list)
        for entry in inventory:
            if entry.relative_path:
                self._by_name[Path(entry.relative_path).name].append(entry)
        self._rows_by_relative_path: dict[str, list[dict[str, str]]] = {}

    def resolve(self, issue: IssueRecord) -> str:
        entry = self._inventory_entry(issue.raw_file)
        if entry is None:
            return ""
        if row_number := _row_number(issue.raw_row_ref):
            row = self._row(entry, row_number)
            if row is not None and entry.date_field:
                row_timestamp = parse_inventory_timestamp(
                    (row.get(entry.date_field) or "").strip(),
                    source_timezone=filename_timezone(Path(entry.relative_path).name),
                )
                if row_timestamp is not None:
                    return format_timestamp(row_timestamp)
        for candidate in _reference_timestamp_candidates(issue.raw_row_ref):
            parsed = parse_inventory_timestamp(candidate, source_timezone=None)
            if parsed is not None:
                return format_timestamp(parsed)
        return ""

    def _inventory_entry(self, raw_file: str) -> FileInventoryEntry | None:
        if not raw_file:
            return None
        if raw_file in self._by_relative_path:
            return self._by_relative_path[raw_file]
        matches = self._by_name.get(Path(raw_file).name, [])
        if len(matches) == 1:
            return matches[0]
        return None

    def _row(self, entry: FileInventoryEntry, row_number: int) -> dict[str, str] | None:
        if row_number < 2:
            return None
        rows = self._rows_for_entry(entry)
        index = row_number - 2
        if index >= len(rows):
            return None
        return rows[index]

    def _rows_for_entry(self, entry: FileInventoryEntry) -> list[dict[str, str]]:
        cached = self._rows_by_relative_path.get(entry.relative_path)
        if cached is not None:
            return cached
        path = self._entry_path(entry)
        rows = [] if path is None else inventory_csv_content(path)[1]
        self._rows_by_relative_path[entry.relative_path] = rows
        return rows

    def _entry_path(self, entry: FileInventoryEntry) -> Path | None:
        if entry.source_path:
            source_path = Path(entry.source_path)
            if source_path.exists():
                return source_path
        candidate = self._raw_dir / entry.relative_path
        if candidate.exists():
            return candidate
        basename_matches = sorted(self._raw_dir.rglob(Path(entry.relative_path).name))
        if len(basename_matches) == 1:
            return basename_matches[0]
        return None


def _row_number(raw_row_ref: str) -> int | None:
    stripped = raw_row_ref.strip()
    if stripped.isdigit():
        return int(stripped)
    match = _ROW_NUMBER_PATTERN.search(stripped)
    if match is None:
        return None
    return int(match.group("row"))


def _reference_timestamp_candidates(raw_row_ref: str) -> tuple[str, ...]:
    seen: set[str] = set()
    candidates: list[str] = []
    for pattern in _TIMESTAMP_PATTERNS:
        for match in pattern.findall(raw_row_ref):
            if match in seen:
                continue
            seen.add(match)
            candidates.append(match)
    return tuple(candidates)
