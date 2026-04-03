"""Coverage inspection for balance reconciliation inputs."""

from __future__ import annotations

from collections import Counter
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
                record.coverage_status == "comparable" for record in records
            ),
        )


def _build_coverage_record(
    artifacts: ArtifactStorePort,
    source_root: Path,
) -> BalanceCoverageRecord:
    snapshot_path = source_root / "balances.csv"
    evidence_path = source_root / "balance_evidence.csv"
    snapshot_rows = (
        artifacts.read_rows(snapshot_path) if snapshot_path.is_file() else []
    )
    evidence_rows = (
        artifacts.read_rows(evidence_path) if evidence_path.is_file() else []
    )
    snapshot_dates = _row_dates(snapshot_rows)
    evidence_dates = _row_dates(evidence_rows)
    return BalanceCoverageRecord(
        source=source_root.name,
        coverage_status=_coverage_status(
            snapshot_exists=snapshot_path.is_file(),
            evidence_exists=evidence_path.is_file(),
            snapshot_count=len(snapshot_rows),
            evidence_count=len(evidence_rows),
        ),
        snapshot_count=len(snapshot_rows),
        evidence_count=len(evidence_rows),
        min_snapshot_date=min(snapshot_dates) if snapshot_dates else "",
        max_snapshot_date=max(snapshot_dates) if snapshot_dates else "",
        min_evidence_date=min(evidence_dates) if evidence_dates else "",
        max_evidence_date=max(evidence_dates) if evidence_dates else "",
    )


def _coverage_status(
    *,
    snapshot_exists: bool,
    evidence_exists: bool,
    snapshot_count: int,
    evidence_count: int,
) -> str:
    if (
        snapshot_exists
        and evidence_exists
        and snapshot_count == 0
        and evidence_count == 0
    ):
        return "empty_source"
    if snapshot_count == 0:
        return "missing_snapshots"
    if evidence_count == 0:
        return "missing_evidence"
    return "comparable"


def _row_dates(rows: list[dict[str, str]]) -> tuple[str, ...]:
    return tuple(
        row["as_of_at"][:10] for row in rows if row.get("as_of_at", "").strip()
    )


def _coverage_summary_payload(
    records: tuple[BalanceCoverageRecord, ...],
) -> dict[str, JsonValue]:
    coverage_status_counts = Counter(record.coverage_status for record in records)
    return {
        "source_count": len(records),
        "comparable_source_count": coverage_status_counts.get("comparable", 0),
        "missing_snapshot_source_count": coverage_status_counts.get(
            "missing_snapshots", 0
        ),
        "missing_evidence_source_count": coverage_status_counts.get(
            "missing_evidence", 0
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
