"""Coverage inspection for balance reconciliation inputs."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from tallylot.application.balances import (
    BALANCE_REFERENCE_FILENAME,
    BALANCE_SNAPSHOT_FILENAME,
)
from tallylot.application.reconciliation.balances.contracts import (
    BalanceCoverageRequest,
    BalanceCoverageResponse,
)
from tallylot.application.reconciliation.balances.records import (
    BALANCE_COVERAGE_HEADER,
    BalanceCoverageRecord,
)
from tallylot.application.reconciliation.balances.sources import (
    discover_balance_source_dirs,
)
from tallylot.application.resource_refs import path_from_ref, to_resource_ref
from tallylot.application.workspace.filesystem import (
    ensure_output_not_within_input_tree,
)
from tallylot.domain.types import JsonValue
from tallylot.ports.artifacts import ArtifactStorePort


@dataclass(frozen=True)
class _CoverageInputs:
    snapshot_exists: bool
    reference_exists: bool
    snapshot_count: int
    reference_row_count: int
    reference_count: int
    missing_reference_count: int
    reference_kind_count: int


class BalanceCoverageWorkflow:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: BalanceCoverageRequest) -> BalanceCoverageResponse:
        input_root = path_from_ref(request.input_root_ref)
        coverage_output_path = path_from_ref(request.coverage_output_ref)
        summary_output_path = coverage_output_path.with_name(
            "balance_coverage_summary.json"
        )
        _ensure_output_paths_are_safe(
            input_root, coverage_output_path, summary_output_path
        )
        _clear_generated_balance_coverage_outputs(coverage_output_path)
        source_dirs = discover_balance_source_dirs(input_root)
        records = tuple(
            _build_coverage_record(self._artifacts, source_dir.root)
            for source_dir in source_dirs
        )
        if records:
            self._artifacts.write_rows(
                coverage_output_path,
                BALANCE_COVERAGE_HEADER,
                (record.to_row() for record in records),
            )
        self._artifacts.write_json(
            summary_output_path,
            _coverage_summary_payload(records),
        )
        return BalanceCoverageResponse(
            coverage_output_ref=request.coverage_output_ref,
            coverage_summary_output_ref=to_resource_ref(summary_output_path),
            source_count=len(records),
            comparable_source_count=sum(
                record.coverage_status in {"resolved_reference", "mixed_reference"}
                for record in records
            ),
        )


def _build_coverage_record(
    artifacts: ArtifactStorePort,
    source_root: Path,
) -> BalanceCoverageRecord:
    snapshot_path = source_root / BALANCE_SNAPSHOT_FILENAME
    reference_path = source_root / BALANCE_REFERENCE_FILENAME
    snapshot_rows = (
        artifacts.read_rows(snapshot_path) if snapshot_path.is_file() else []
    )
    reference_rows = (
        artifacts.read_rows(reference_path) if reference_path.is_file() else []
    )
    snapshot_dates = _row_dates(snapshot_rows)
    reference_dates = _reference_dates(reference_rows)
    snapshot_keys = _logical_keys(snapshot_rows)
    references_by_kind = _reference_keys_by_kind(reference_rows)
    resolved_reference_keys: set[tuple[str, ...]] = set()
    for kind_keys in references_by_kind.values():
        resolved_reference_keys.update(kind_keys)
    missing_reference_count = len(snapshot_keys - resolved_reference_keys)
    coverage_inputs = _CoverageInputs(
        snapshot_exists=snapshot_path.is_file(),
        reference_exists=reference_path.is_file(),
        snapshot_count=len(snapshot_rows),
        reference_row_count=len(reference_rows),
        reference_count=len(snapshot_keys & resolved_reference_keys),
        missing_reference_count=missing_reference_count,
        reference_kind_count=sum(
            1 for kind_keys in references_by_kind.values() if kind_keys
        ),
    )
    return BalanceCoverageRecord(
        source=source_root.name,
        coverage_status=_coverage_status(coverage_inputs),
        snapshot_count=len(snapshot_rows),
        reference_count=len(reference_rows),
        source_document_count=len(
            snapshot_keys & references_by_kind["source_document"]
        ),
        network_api_count=len(snapshot_keys & references_by_kind["network_api"]),
        operator_assertion_count=len(
            snapshot_keys & references_by_kind["operator_assertion"]
        ),
        missing_reference_count=missing_reference_count,
        min_snapshot_date=min(snapshot_dates) if snapshot_dates else "",
        max_snapshot_date=max(snapshot_dates) if snapshot_dates else "",
        min_reference_date=min(reference_dates) if reference_dates else "",
        max_reference_date=max(reference_dates) if reference_dates else "",
    )


def _coverage_status(inputs: _CoverageInputs) -> str:
    if (
        inputs.snapshot_exists
        and inputs.reference_exists
        and inputs.snapshot_count == 0
        and inputs.reference_row_count == 0
    ):
        status = "empty_source"
    elif inputs.snapshot_count == 0:
        status = "missing_snapshots"
    elif inputs.missing_reference_count > 0 or inputs.reference_count == 0:
        status = "missing_reference"
    elif inputs.reference_kind_count > 1:
        status = "mixed_reference"
    else:
        status = "resolved_reference"
    return status


def _row_dates(rows: list[dict[str, str]]) -> tuple[str, ...]:
    return tuple(
        row["target_at"][:10] for row in rows if row.get("target_at", "").strip()
    )


def _logical_keys(rows: list[dict[str, str]]) -> set[tuple[str, ...]]:
    return {
        (
            row.get("source", "").strip(),
            row.get("location_id", "").strip(),
            row.get("instrument_id", "").strip(),
            row.get("balance_kind", "").strip() or "available",
            row.get("target_at", "").strip(),
            row.get("target_precision", "").strip(),
        )
        for row in rows
    }


def _reference_dates(rows: list[dict[str, str]]) -> tuple[str, ...]:
    return tuple(
        row["observed_at"][:10] for row in rows if row.get("observed_at", "").strip()
    )


def _reference_keys_by_kind(
    rows: list[dict[str, str]],
) -> dict[str, set[tuple[str, ...]]]:
    grouped: dict[str, set[tuple[str, ...]]] = {
        "source_document": set(),
        "network_api": set(),
        "operator_assertion": set(),
    }
    for row in rows:
        reference_kind = row.get("reference_kind", "").strip()
        if reference_kind not in grouped:
            continue
        grouped[reference_kind].add(
            (
                row.get("source", "").strip(),
                row.get("location_id", "").strip(),
                row.get("instrument_id", "").strip(),
                row.get("balance_kind", "").strip() or "available",
                row.get("target_at", "").strip(),
                row.get("target_precision", "").strip(),
            )
        )
    return grouped


def _coverage_summary_payload(
    records: tuple[BalanceCoverageRecord, ...],
) -> dict[str, JsonValue]:
    coverage_status_counts = Counter(record.coverage_status for record in records)
    return {
        "source_count": len(records),
        "comparable_source_count": sum(
            coverage_status_counts.get(status, 0)
            for status in ("resolved_reference", "mixed_reference")
        ),
        "resolved_reference_source_count": coverage_status_counts.get(
            "resolved_reference", 0
        ),
        "mixed_reference_source_count": coverage_status_counts.get(
            "mixed_reference", 0
        ),
        "missing_snapshot_source_count": coverage_status_counts.get(
            "missing_snapshots", 0
        ),
        "missing_reference_source_count": coverage_status_counts.get(
            "missing_reference", 0
        ),
        "empty_source_count": coverage_status_counts.get("empty_source", 0),
    }


def _ensure_output_paths_are_safe(input_root: Path, *output_paths: Path) -> None:
    for output_path in output_paths:
        ensure_output_not_within_input_tree(
            input_root,
            output_path,
            input_label="balance input root",
            output_label="balance coverage output",
        )


def _clear_generated_balance_coverage_outputs(coverage_output_path: Path) -> None:
    for path in (
        coverage_output_path,
        coverage_output_path.with_name("balance_coverage_summary.json"),
    ):
        if path.is_file() or path.is_symlink():
            path.unlink()
