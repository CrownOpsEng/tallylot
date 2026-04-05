"""Coverage inspection for balance reconciliation inputs."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

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
    evidence_exists: bool
    confirmation_exists: bool
    snapshot_count: int
    reference_row_count: int
    reference_count: int
    missing_reference_count: int


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
        source_dirs = discover_balance_source_dirs(input_root)
        records = tuple(
            _build_coverage_record(self._artifacts, source_dir.root)
            for source_dir in source_dirs
        )
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
                record.coverage_status
                in {"source_backed", "operator_confirmed", "mixed_reference"}
                for record in records
            ),
        )


def _build_coverage_record(
    artifacts: ArtifactStorePort,
    source_root: Path,
) -> BalanceCoverageRecord:
    snapshot_path = source_root / "balances.csv"
    evidence_path = source_root / "balance_evidence.csv"
    confirmation_path = source_root / "balance_confirmations.csv"
    snapshot_rows = (
        artifacts.read_rows(snapshot_path) if snapshot_path.is_file() else []
    )
    evidence_rows = (
        artifacts.read_rows(evidence_path) if evidence_path.is_file() else []
    )
    confirmation_rows = (
        artifacts.read_rows(confirmation_path) if confirmation_path.is_file() else []
    )
    snapshot_dates = _row_dates(snapshot_rows)
    evidence_dates = _row_dates(evidence_rows)
    snapshot_keys = _logical_keys(snapshot_rows)
    evidence_keys = _logical_keys(evidence_rows)
    confirmation_keys = _logical_keys(confirmation_rows)
    source_backed_reference_count = len(snapshot_keys & evidence_keys)
    operator_confirmation_count = len(
        (snapshot_keys - evidence_keys) & confirmation_keys
    )
    missing_reference_count = len(snapshot_keys - evidence_keys - confirmation_keys)
    coverage_inputs = _CoverageInputs(
        snapshot_exists=snapshot_path.is_file(),
        evidence_exists=evidence_path.is_file(),
        confirmation_exists=confirmation_path.is_file(),
        snapshot_count=len(snapshot_rows),
        reference_row_count=len(evidence_rows) + len(confirmation_rows),
        reference_count=source_backed_reference_count + operator_confirmation_count,
        missing_reference_count=missing_reference_count,
    )
    return BalanceCoverageRecord(
        source=source_root.name,
        coverage_status=_coverage_status(coverage_inputs),
        snapshot_count=len(snapshot_rows),
        evidence_count=len(evidence_rows),
        source_backed_reference_count=source_backed_reference_count,
        operator_confirmation_count=operator_confirmation_count,
        missing_reference_count=missing_reference_count,
        min_snapshot_date=min(snapshot_dates) if snapshot_dates else "",
        max_snapshot_date=max(snapshot_dates) if snapshot_dates else "",
        min_evidence_date=min(evidence_dates) if evidence_dates else "",
        max_evidence_date=max(evidence_dates) if evidence_dates else "",
    )


def _coverage_status(inputs: _CoverageInputs) -> str:
    if (
        inputs.snapshot_exists
        and (inputs.evidence_exists or inputs.confirmation_exists)
        and inputs.snapshot_count == 0
        and inputs.reference_row_count == 0
    ):
        status = "empty_source"
    elif inputs.snapshot_count == 0:
        status = "missing_snapshots"
    elif inputs.missing_reference_count > 0 or inputs.reference_count == 0:
        status = "missing_reference"
    elif inputs.evidence_exists and inputs.confirmation_exists:
        status = "mixed_reference"
    elif inputs.evidence_exists:
        status = "source_backed"
    else:
        status = "operator_confirmed"
    return status


def _row_dates(rows: list[dict[str, str]]) -> tuple[str, ...]:
    return tuple(
        row["as_of_at"][:10] for row in rows if row.get("as_of_at", "").strip()
    )


def _logical_keys(rows: list[dict[str, str]]) -> set[tuple[str, ...]]:
    return {
        (
            row.get("source", "").strip(),
            row.get("location_id", "").strip(),
            row.get("instrument_id", "").strip(),
            row.get("quantity", "").strip(),
            row.get("as_of_at", "").strip(),
            row.get("as_of_precision", "").strip(),
            row.get("balance_kind", "").strip() or "available",
        )
        for row in rows
    }


def _coverage_summary_payload(
    records: tuple[BalanceCoverageRecord, ...],
) -> dict[str, JsonValue]:
    coverage_status_counts = Counter(record.coverage_status for record in records)
    return {
        "source_count": len(records),
        "comparable_source_count": sum(
            coverage_status_counts.get(status, 0)
            for status in ("source_backed", "operator_confirmed", "mixed_reference")
        ),
        "source_backed_source_count": coverage_status_counts.get("source_backed", 0),
        "operator_confirmed_source_count": coverage_status_counts.get(
            "operator_confirmed", 0
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
