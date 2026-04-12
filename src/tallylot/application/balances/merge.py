"""Shared balance merge policy and deterministic artifact dedupe helpers."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import overload

from tallylot.application.balances.filenames import (
    BALANCE_REFERENCE_FILENAME,
    BALANCE_SNAPSHOT_FILENAME,
)
from tallylot.domain.balances import BalanceReference, BalanceSnapshot
from tallylot.domain.issues import IssueRecord
from tallylot.domain.value_objects import (
    format_decimal,
    format_temporal_value,
    format_timestamp,
)
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.evidence import (
    BALANCE_REFERENCE_HEADER,
    BALANCE_SNAPSHOT_HEADER,
)

BalanceSnapshotSemanticKey = tuple[str, str, str, str, str, str]
BalanceReferenceSemanticKey = tuple[str, ...]


@dataclass(frozen=True)
class _BalanceCsvMergeSpec:
    artifacts: ArtifactStorePort
    roots: tuple[Path, ...]
    source: str
    filename: str
    header: tuple[str, ...]
    semantic_key: Callable[[Mapping[str, str]], tuple[str, ...]]
    conflict_key: Callable[[Mapping[str, str]], str]
    conflict_message: str


@overload
def balance_snapshot_semantic_key(
    value: Mapping[str, str],
) -> BalanceSnapshotSemanticKey: ...


@overload
def balance_snapshot_semantic_key(
    value: BalanceSnapshot,
) -> BalanceSnapshotSemanticKey: ...


def balance_snapshot_semantic_key(
    value: Mapping[str, str] | BalanceSnapshot,
) -> BalanceSnapshotSemanticKey:
    if isinstance(value, BalanceSnapshot):
        target = value.target
        return (
            str(target.source).strip(),
            str(target.location_id).strip(),
            str(target.instrument_id).strip(),
            str(target.balance_kind).strip() or "available",
            format_temporal_value(
                target.target_at,
                precision=target.target_precision,
                label="balance target target_at",
            ),
            target.target_precision.value,
        )
    return (
        _text(value, "source"),
        _text(value, "location_id"),
        _text(value, "instrument_id"),
        _text(value, "balance_kind") or "available",
        _text(value, "target_at"),
        _text(value, "target_precision"),
    )


@overload
def balance_snapshot_conflict_key(value: Mapping[str, str]) -> str: ...


@overload
def balance_snapshot_conflict_key(value: BalanceSnapshot) -> str: ...


def balance_snapshot_conflict_key(
    value: Mapping[str, str] | BalanceSnapshot,
) -> str:
    if isinstance(value, BalanceSnapshot):
        return format_decimal(value.quantity)
    return _text(value, "quantity")


@overload
def balance_reference_semantic_key(
    value: Mapping[str, str],
) -> BalanceReferenceSemanticKey: ...


@overload
def balance_reference_semantic_key(
    value: BalanceReference,
) -> BalanceReferenceSemanticKey: ...


def balance_reference_semantic_key(
    value: Mapping[str, str] | BalanceReference,
) -> BalanceReferenceSemanticKey:
    if isinstance(value, BalanceReference):
        target = value.target
        return (
            str(target.source).strip(),
            str(target.location_id).strip(),
            str(target.instrument_id).strip(),
            str(target.balance_kind).strip() or "available",
            format_temporal_value(
                target.target_at,
                precision=target.target_precision,
                label="balance target target_at",
            ),
            target.target_precision.value,
            value.reference_kind.value,
            format_temporal_value(
                value.observed_at,
                precision=value.observed_precision,
                label="balance reference observed_at",
            ),
            value.observed_precision.value,
            value.support_ref,
            value.provider_family,
            value.provider_locator,
            value.provider_block_ref,
            value.reviewed_by,
            "" if value.reviewed_at is None else format_timestamp(value.reviewed_at),
        )
    return (
        _text(value, "source"),
        _text(value, "location_id"),
        _text(value, "instrument_id"),
        _text(value, "balance_kind") or "available",
        _text(value, "target_at"),
        _text(value, "target_precision"),
        _text(value, "reference_kind"),
        _text(value, "observed_at"),
        _text(value, "observed_precision"),
        _text(value, "support_ref"),
        _text(value, "provider_family"),
        _text(value, "provider_locator"),
        _text(value, "provider_block_ref"),
        _text(value, "reviewed_by"),
        _text(value, "reviewed_at"),
    )


@overload
def balance_reference_conflict_key(value: Mapping[str, str]) -> str: ...


@overload
def balance_reference_conflict_key(value: BalanceReference) -> str: ...


def balance_reference_conflict_key(
    value: Mapping[str, str] | BalanceReference,
) -> str:
    if isinstance(value, BalanceReference):
        return format_decimal(value.quantity)
    return _text(value, "quantity")


def merge_balance_snapshot_rows(
    artifacts: ArtifactStorePort,
    roots: tuple[Path, ...],
    *,
    source: str,
) -> tuple[tuple[dict[str, str], ...], tuple[IssueRecord, ...]]:
    return _merge_balance_csv_rows(
        _BalanceCsvMergeSpec(
            artifacts=artifacts,
            roots=roots,
            source=source,
            filename=BALANCE_SNAPSHOT_FILENAME,
            header=BALANCE_SNAPSHOT_HEADER,
            semantic_key=balance_snapshot_semantic_key,
            conflict_key=balance_snapshot_conflict_key,
            conflict_message=(
                "Source assembly found conflicting balance snapshot rows for the same "
                "semantic key."
            ),
        )
    )


def merge_balance_reference_rows(
    artifacts: ArtifactStorePort,
    roots: tuple[Path, ...],
    *,
    source: str,
) -> tuple[tuple[dict[str, str], ...], tuple[IssueRecord, ...]]:
    return _merge_balance_csv_rows(
        _BalanceCsvMergeSpec(
            artifacts=artifacts,
            roots=roots,
            source=source,
            filename=BALANCE_REFERENCE_FILENAME,
            header=BALANCE_REFERENCE_HEADER,
            semantic_key=balance_reference_semantic_key,
            conflict_key=balance_reference_conflict_key,
            conflict_message=(
                "Source assembly found conflicting balance reference rows for the same "
                "semantic key."
            ),
        )
    )


def merge_balance_snapshots(
    *,
    existing_snapshots: tuple[BalanceSnapshot, ...],
    submitted_snapshots: tuple[BalanceSnapshot, ...],
) -> tuple[BalanceSnapshot, ...]:
    merged: dict[BalanceSnapshotSemanticKey, BalanceSnapshot] = {
        balance_snapshot_semantic_key(item): item
        for item in (*existing_snapshots, *submitted_snapshots)
    }
    return tuple(merged[key] for key in sorted(merged))


def merge_balance_references(
    *,
    existing_references: tuple[BalanceReference, ...],
    submitted_references: tuple[BalanceReference, ...],
) -> tuple[BalanceReference, ...]:
    merged: dict[BalanceReferenceSemanticKey, BalanceReference] = {
        balance_reference_semantic_key(item): item
        for item in (*existing_references, *submitted_references)
    }
    return tuple(merged[key] for key in sorted(merged))


def _merge_balance_csv_rows(
    spec: _BalanceCsvMergeSpec,
) -> tuple[tuple[dict[str, str], ...], tuple[IssueRecord, ...]]:
    rows = tuple(
        row
        for root in spec.roots
        if (root / spec.filename).is_file()
        for row in spec.artifacts.read_rows(root / spec.filename)
    )
    merged = _dedupe_rows(rows, header=spec.header)
    issues = _conflict_issues(spec, merged)
    return merged, issues


def _dedupe_rows(
    rows: tuple[dict[str, str], ...],
    *,
    header: tuple[str, ...],
) -> tuple[dict[str, str], ...]:
    seen: set[tuple[str, ...]] = set()
    merged: list[dict[str, str]] = []
    for row in sorted(rows, key=lambda item: _row_tuple(item, header)):
        key = _row_tuple(row, header)
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)
    return tuple(merged)


def _conflict_issues(
    spec: _BalanceCsvMergeSpec,
    rows: tuple[dict[str, str], ...],
) -> tuple[IssueRecord, ...]:
    conflict_values: dict[tuple[str, ...], set[str]] = defaultdict(set)
    for row in rows:
        key = spec.semantic_key(row)
        if key:
            conflict_values[key].add(spec.conflict_key(row))
    issues: list[IssueRecord] = []
    for index, (key, values) in enumerate(
        sorted(conflict_values.items(), key=lambda item: item[0]),
        start=1,
    ):
        if len(values) <= 1:
            continue
        issues.append(
            IssueRecord(
                issue_id=f"assembly:{spec.source}:{spec.filename}:{index}",
                source=spec.source,
                adapter_id="source_assembly",
                severity="high",
                kind="assembly_semantic_conflict",
                message=spec.conflict_message,
                raw_file=spec.filename,
                raw_row_ref=str(key),
            )
        )
    return tuple(issues)


def _row_tuple(row: Mapping[str, str], header: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(row.get(column, "") for column in header)


def _text(row: Mapping[str, str], key: str) -> str:
    return row.get(key, "").strip()
