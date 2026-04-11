"""Normalization issue and review context enrichment."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from tallylot.application.profiling.csv_inventory import (
    filename_timezone,
    inventory_csv_content,
    parse_inventory_timestamp,
)
from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.value_objects import format_timestamp
from tallylot.ports.source_profiles import FileInventoryEntry

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
    resolver = _ContextTimestampResolver(raw_dir=raw_dir, inventory=inventory)
    enriched: list[IssueRecord] = []
    for issue in issues:
        if issue.context_timestamp:
            enriched.append(issue)
            continue
        context_timestamp = resolver.resolve(
            issue.raw_file,
            issue.raw_row_ref,
            raw_provenance=issue.raw_provenance,
        )
        enriched.append(
            issue
            if not context_timestamp
            else replace(issue, context_timestamp=context_timestamp)
        )
    return tuple(enriched)


def enrich_review_context_timestamps(
    reviews: tuple[NormalizationReviewRecord, ...],
    *,
    raw_dir: Path,
    inventory: tuple[FileInventoryEntry, ...],
) -> tuple[NormalizationReviewRecord, ...]:
    resolver = _ContextTimestampResolver(raw_dir=raw_dir, inventory=inventory)
    enriched: list[NormalizationReviewRecord] = []
    for review in reviews:
        if review.context_timestamp:
            enriched.append(review)
            continue
        context_timestamp = resolver.resolve(
            review.raw_file,
            review.raw_row_ref,
            raw_provenance=review.raw_provenance,
        )
        enriched.append(
            review
            if not context_timestamp
            else replace(review, context_timestamp=context_timestamp)
        )
    return tuple(enriched)


class _ContextTimestampResolver:
    def __init__(
        self, *, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]
    ) -> None:
        self._raw_dir = raw_dir
        self._by_reference = _inventory_references(inventory)
        self._rows_by_relative_path: dict[str, list[dict[str, str]]] = {}

    def resolve(
        self,
        raw_file: str,
        raw_row_ref: str,
        *,
        raw_provenance: ProvenanceLocator | None = None,
    ) -> str:
        entry = self._inventory_entry(raw_file, raw_provenance=raw_provenance)
        if entry is None:
            return ""
        if row_number := _row_number(raw_row_ref):
            row = self._row(entry, row_number)
            if row is not None and entry.date_field:
                row_timestamp = parse_inventory_timestamp(
                    (row.get(entry.date_field) or "").strip(),
                    source_timezone=filename_timezone(Path(entry.relative_path).name),
                )
                if row_timestamp is not None:
                    return format_timestamp(row_timestamp)
        for candidate in _reference_timestamp_candidates(raw_row_ref):
            parsed = parse_inventory_timestamp(candidate, source_timezone=None)
            if parsed is not None:
                return format_timestamp(parsed)
        return ""

    def _inventory_entry(
        self,
        raw_file: str,
        *,
        raw_provenance: ProvenanceLocator | None,
    ) -> FileInventoryEntry | None:
        if raw_provenance is not None:
            entry = self._by_reference.get(raw_provenance.relative_path)
            if entry is not None:
                return entry
        if not raw_file:
            return None
        return self._by_reference.get(raw_file) or self._by_reference.get(
            raw_file.replace("\\", "/")
        )

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
        return None


def _inventory_references(
    inventory: tuple[FileInventoryEntry, ...],
) -> dict[str, FileInventoryEntry]:
    references: dict[str, FileInventoryEntry] = {}
    for entry in inventory:
        for reference in (
            entry.relative_path,
            entry.source_path,
            entry.archive_source_path,
        ):
            if reference and reference not in references:
                references[reference] = entry
    return references


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
