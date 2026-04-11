"""Inspection for balance reconciliation inputs."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from tallylot.application.balances.contracts import (
    BalanceInspectRequest,
    BalanceInspectResponse,
)
from tallylot.application.balances.filenames import (
    BALANCE_REFERENCE_FILENAME,
    BALANCE_SNAPSHOT_FILENAME,
)
from tallylot.application.balances.inputs import (
    BalanceSourceInputs,
    build_balance_source_inputs,
    discover_balance_source_dirs,
)
from tallylot.application.balances.records import (
    BALANCE_INSPECT_HEADER,
    BalanceInspectRecord,
)
from tallylot.application.resource_refs import path_from_ref, to_resource_ref
from tallylot.application.workspace.filesystem import (
    ensure_output_not_within_input_tree,
)
from tallylot.domain.balances import BalanceReference, BalanceSnapshot
from tallylot.domain.types import JsonValue
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.evidence import EvidenceRepositoryPort
from tallylot.ports.facts import FactRepositoryPort


@dataclass(frozen=True)
class _InspectInputs:
    snapshot_exists: bool
    reference_exists: bool
    snapshot_count: int
    reference_row_count: int
    reference_count: int
    missing_reference_count: int
    reference_kind_count: int


class BalanceInspectWorkflow:
    def __init__(
        self,
        *,
        facts: FactRepositoryPort,
        evidence: EvidenceRepositoryPort,
        artifacts: ArtifactStorePort,
    ) -> None:
        self._facts = facts
        self._evidence = evidence
        self._artifacts = artifacts

    def execute(self, request: BalanceInspectRequest) -> BalanceInspectResponse:
        input_root = path_from_ref(request.input_root_ref)
        inspect_output_path = path_from_ref(request.inspect_output_ref)
        summary_output_path = inspect_output_path.with_name(
            "balance_inspect_summary.json"
        )
        _ensure_output_paths_are_safe(
            input_root, inspect_output_path, summary_output_path
        )
        _clear_generated_balance_inspect_outputs(inspect_output_path)
        source_dirs = discover_balance_source_dirs(input_root)
        source_inputs = tuple(
            build_balance_source_inputs(
                source_dir,
                facts=self._facts,
                evidence=self._evidence,
                artifacts=self._artifacts,
            )
            for source_dir in source_dirs
        )
        records = tuple(
            _build_inspect_record(source_input) for source_input in source_inputs
        )
        if records:
            self._artifacts.write_rows(
                inspect_output_path,
                BALANCE_INSPECT_HEADER,
                (record.to_row() for record in records),
            )
        self._artifacts.write_json(
            summary_output_path,
            _inspect_summary_payload(records),
        )
        return BalanceInspectResponse(
            inspect_output_ref=request.inspect_output_ref,
            inspect_summary_output_ref=to_resource_ref(summary_output_path),
            source_count=len(records),
            comparable_source_count=sum(
                record.inspect_status in {"resolved_reference", "mixed_reference"}
                for record in records
            ),
        )


def _build_inspect_record(
    source_input: BalanceSourceInputs,
) -> BalanceInspectRecord:
    snapshot_exists = (source_input.root / BALANCE_SNAPSHOT_FILENAME).is_file()
    reference_exists = (source_input.root / BALANCE_REFERENCE_FILENAME).is_file()
    snapshot_rows = source_input.snapshots
    reference_rows = source_input.references
    snapshot_dates = _row_dates(snapshot_rows)
    reference_dates = _reference_dates(reference_rows)
    snapshot_keys = _logical_keys(snapshot_rows)
    references_by_kind = _reference_keys_by_kind(reference_rows)
    resolved_reference_keys: set[tuple[str, ...]] = set()
    for kind_keys in references_by_kind.values():
        resolved_reference_keys.update(kind_keys)
    missing_reference_count = len(snapshot_keys - resolved_reference_keys)
    inspect_inputs = _InspectInputs(
        snapshot_exists=snapshot_exists,
        reference_exists=reference_exists,
        snapshot_count=len(snapshot_rows),
        reference_row_count=len(reference_rows),
        reference_count=len(snapshot_keys & resolved_reference_keys),
        missing_reference_count=missing_reference_count,
        reference_kind_count=sum(
            1 for kind_keys in references_by_kind.values() if kind_keys
        ),
    )
    return BalanceInspectRecord(
        source=source_input.source,
        inspect_status=_inspect_status(inspect_inputs),
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


def _inspect_status(inputs: _InspectInputs) -> str:
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


def _row_dates(rows: tuple[BalanceSnapshot, ...]) -> tuple[str, ...]:
    return tuple(
        str(row.target.target_at)[:10]
        for row in rows
        if str(row.target.target_at).strip()
    )


def _logical_keys(rows: tuple[BalanceSnapshot, ...]) -> set[tuple[str, ...]]:
    return {
        (
            str(row.target.source).strip(),
            str(row.target.location_id).strip(),
            str(row.target.instrument_id).strip(),
            str(row.target.balance_kind).strip() or "available",
            str(row.target.target_at).strip(),
            row.target.target_precision.value,
        )
        for row in rows
    }


def _reference_dates(rows: tuple[BalanceReference, ...]) -> tuple[str, ...]:
    return tuple(
        str(row.observed_at)[:10] for row in rows if str(row.observed_at).strip()
    )


def _reference_keys_by_kind(
    rows: tuple[BalanceReference, ...],
) -> dict[str, set[tuple[str, ...]]]:
    grouped: dict[str, set[tuple[str, ...]]] = {
        "source_document": set(),
        "network_api": set(),
        "operator_assertion": set(),
    }
    for row in rows:
        reference_kind = row.reference_kind.value
        if reference_kind not in grouped:
            continue
        grouped[reference_kind].add(
            (
                str(row.target.source).strip(),
                str(row.target.location_id).strip(),
                str(row.target.instrument_id).strip(),
                str(row.target.balance_kind).strip() or "available",
                str(row.target.target_at).strip(),
                row.target.target_precision.value,
            )
        )
    return grouped


def _inspect_summary_payload(
    records: tuple[BalanceInspectRecord, ...],
) -> dict[str, JsonValue]:
    inspect_status_counts = Counter(record.inspect_status for record in records)
    return {
        "source_count": len(records),
        "comparable_source_count": sum(
            inspect_status_counts.get(status, 0)
            for status in ("resolved_reference", "mixed_reference")
        ),
        "resolved_reference_source_count": inspect_status_counts.get(
            "resolved_reference", 0
        ),
        "mixed_reference_source_count": inspect_status_counts.get("mixed_reference", 0),
        "missing_snapshot_source_count": inspect_status_counts.get(
            "missing_snapshots", 0
        ),
        "missing_reference_source_count": inspect_status_counts.get(
            "missing_reference", 0
        ),
        "empty_source_count": inspect_status_counts.get("empty_source", 0),
    }


def _ensure_output_paths_are_safe(input_root: Path, *output_paths: Path) -> None:
    for output_path in output_paths:
        ensure_output_not_within_input_tree(
            input_root,
            output_path,
            input_label="balance input root",
            output_label="balance inspect output",
        )


def _clear_generated_balance_inspect_outputs(inspect_output_path: Path) -> None:
    for path in (
        inspect_output_path,
        inspect_output_path.with_name("balance_inspect_summary.json"),
    ):
        if path.is_file() or path.is_symlink():
            path.unlink()
