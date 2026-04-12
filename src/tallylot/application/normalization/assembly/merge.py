"""Deterministic row merge helpers for source assembly."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import cast

from tallylot.domain.issues import IssueRecord
from tallylot.ports.artifacts import ArtifactStorePort


@dataclass(frozen=True)
class ConflictPolicy:
    semantic_key: Callable[[dict[str, str]], object]
    conflict_key: Callable[[dict[str, str]], object]
    message: str


@dataclass(frozen=True)
class CsvArtifactMergeSpec:
    filename: str
    header: tuple[str, ...]
    conflict_policy: ConflictPolicy | None = None


def merge_csv_artifact(
    artifacts: ArtifactStorePort,
    roots: tuple[Path, ...],
    spec: CsvArtifactMergeSpec,
    source: str,
) -> tuple[tuple[dict[str, str], ...], tuple[IssueRecord, ...]]:
    rows = tuple(
        row
        for root in roots
        if (root / spec.filename).is_file()
        for row in artifacts.read_rows(root / spec.filename)
    )
    merged = _dedupe_rows(rows, header=spec.header)
    if spec.conflict_policy is None:
        return merged, ()
    issues = _conflict_issues(
        merged,
        artifact_name=spec.filename,
        source=source,
        policy=spec.conflict_policy,
    )
    return merged, issues


def merge_json_array_artifact(
    roots: tuple[Path, ...],
    *,
    filename: str,
) -> list[object]:
    merged: list[object] = []
    seen: set[str] = set()
    for root in roots:
        path = root / filename
        if not path.is_file():
            continue
        payload: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"{filename} must contain a JSON array: {path}")
        for item in cast(list[object], payload):
            key = json.dumps(item, sort_keys=True, separators=(",", ":"))
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return sorted(
        merged,
        key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
    )


def row_key(row: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(row.items()))


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
    rows: tuple[dict[str, str], ...],
    *,
    artifact_name: str,
    source: str,
    policy: ConflictPolicy,
) -> tuple[IssueRecord, ...]:
    conflict_values: dict[object, set[object]] = defaultdict(set)
    for row in rows:
        key = policy.semantic_key(row)
        if key:
            conflict_values[key].add(policy.conflict_key(row))
    issues: list[IssueRecord] = []
    for index, (key, values) in enumerate(
        sorted(conflict_values.items(), key=str), start=1
    ):
        if len(values) <= 1:
            continue
        issues.append(
            IssueRecord(
                issue_id=f"assembly:{source}:{artifact_name}:{index}",
                source=source,
                adapter_id="source_assembly",
                severity="high",
                kind="assembly_semantic_conflict",
                message=policy.message,
                raw_file=artifact_name,
                raw_row_ref=str(key),
            )
        )
    return tuple(issues)


def _row_tuple(row: Mapping[str, str], header: Iterable[str]) -> tuple[str, ...]:
    return tuple(row.get(column, "") for column in header)
