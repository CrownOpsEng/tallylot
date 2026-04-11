"""Inspection for balance reconciliation inputs."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from tallylot.application.balances.contracts import (
    BalanceInspectRequest,
    BalanceInspectResponse,
)
from tallylot.application.balances.inputs import (
    BalanceSourceInputs,
    build_balance_source_inputs,
    discover_balance_source_dirs,
)
from tallylot.application.balances.records import (
    BALANCE_INSPECT_HEADER,
    BalanceCrossSourceReadyStatus,
    BalanceOfflineReadyStatus,
    BalanceInspectRecord,
)
from tallylot.application.resource_refs import path_from_ref, to_resource_ref
from tallylot.application.workspace.filesystem import (
    ensure_output_not_within_input_tree,
)
from tallylot.domain.balances import BalanceReference, BalanceSnapshot, BalanceTarget
from tallylot.domain.types import JsonValue
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.evidence import EvidenceRepositoryPort
from tallylot.ports.facts import FactRepositoryPort


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
                record.cross_source_ready == "ready" for record in records
            ),
        )


def _build_inspect_record(
    source_input: BalanceSourceInputs,
) -> BalanceInspectRecord:
    target_keys = _target_keys(source_input.targets)
    snapshot_keys = _snapshot_keys(source_input.snapshots)
    reference_row_count = len(source_input.references)
    reference_keys_by_kind = _reference_keys_by_kind(source_input.references)
    all_reference_keys: set[tuple[str, str, str, str, str, str]] = set()
    for reference_keys in reference_keys_by_kind.values():
        all_reference_keys.update(reference_keys)
    matched_reference_count = len(target_keys & all_reference_keys)
    missing_reference_count = len(target_keys) - matched_reference_count
    offline_ready = _offline_ready_status(
        source_input=source_input,
        target_count=len(target_keys),
        matched_reference_count=matched_reference_count,
    )
    cross_source_ready = _cross_source_ready_status(
        source_input=source_input,
        target_count=len(target_keys),
        snapshot_count=len(snapshot_keys),
    )
    return BalanceInspectRecord(
        source=source_input.source,
        input_mode=source_input.input_mode,
        snapshot_origin=source_input.snapshot_origin,
        target_count=len(target_keys),
        snapshot_count=len(snapshot_keys),
        reference_row_count=reference_row_count,
        matched_reference_count=matched_reference_count,
        missing_reference_count=missing_reference_count,
        source_document_count=len(
            target_keys & reference_keys_by_kind["source_document"]
        ),
        network_api_count=len(target_keys & reference_keys_by_kind["network_api"]),
        operator_assertion_count=len(
            target_keys & reference_keys_by_kind["operator_assertion"]
        ),
        cross_source_ready=cross_source_ready,
        offline_ready=offline_ready,
        unexpected_superseded_output_count=len(
            source_input.unexpected_superseded_outputs
        ),
        min_target_date=min(_target_dates(source_input.targets))
        if source_input.targets
        else "",
        max_target_date=max(_target_dates(source_input.targets))
        if source_input.targets
        else "",
        min_reference_date=min(_reference_dates(source_input.references))
        if source_input.references
        else "",
        max_reference_date=max(_reference_dates(source_input.references))
        if source_input.references
        else "",
    )


def _offline_ready_status(
    *,
    source_input: BalanceSourceInputs,
    target_count: int,
    matched_reference_count: int,
) -> BalanceOfflineReadyStatus:
    if source_input.input_mode == "empty":
        return "no_balance_inputs"
    if target_count == 0:
        return "no_balance_targets"
    if matched_reference_count < target_count:
        return "missing_references"
    return "ready"


def _cross_source_ready_status(
    *,
    source_input: BalanceSourceInputs,
    target_count: int,
    snapshot_count: int,
) -> BalanceCrossSourceReadyStatus:
    if source_input.input_mode == "empty":
        return "not_applicable"
    if not source_input.location_inventory:
        return "missing_location_inventory"
    if target_count == 0 or snapshot_count == 0:
        return "not_comparable"
    return "ready"


def _target_keys(
    targets: tuple[BalanceTarget, ...],
) -> set[tuple[str, str, str, str, str, str]]:
    return {_target_key(target) for target in targets}


def _snapshot_keys(
    snapshots: tuple[BalanceSnapshot, ...],
) -> set[tuple[str, str, str, str, str, str]]:
    return {_target_key(snapshot.target) for snapshot in snapshots}


def _target_key(
    target: BalanceTarget,
) -> tuple[str, str, str, str, str, str]:
    return (
        str(target.source).strip(),
        str(target.location_id).strip(),
        str(target.instrument_id).strip(),
        str(target.balance_kind).strip() or "available",
        str(target.target_at).strip(),
        target.target_precision.value,
    )


def _reference_keys_by_kind(
    rows: tuple[BalanceReference, ...],
) -> dict[str, set[tuple[str, str, str, str, str, str]]]:
    grouped: dict[str, set[tuple[str, str, str, str, str, str]]] = {
        "source_document": set(),
        "network_api": set(),
        "operator_assertion": set(),
    }
    for row in rows:
        reference_kind = row.reference_kind.value
        if reference_kind not in grouped:
            continue
        grouped[reference_kind].add(_target_key(row.target))
    return grouped


def _target_dates(rows: tuple[BalanceTarget, ...]) -> tuple[str, ...]:
    return tuple(str(row.target_at)[:10] for row in rows if str(row.target_at).strip())


def _reference_dates(rows: tuple[BalanceReference, ...]) -> tuple[str, ...]:
    return tuple(
        str(row.observed_at)[:10] for row in rows if str(row.observed_at).strip()
    )


def _inspect_summary_payload(
    records: tuple[BalanceInspectRecord, ...],
) -> dict[str, JsonValue]:
    offline_ready_counts = Counter(record.offline_ready for record in records)
    cross_source_ready_counts = Counter(record.cross_source_ready for record in records)
    input_mode_counts = Counter(record.input_mode for record in records)
    snapshot_origin_counts = Counter(record.snapshot_origin for record in records)
    return {
        "source_count": len(records),
        "inspect_status_counts": dict(sorted(offline_ready_counts.items())),
        "cross_source_ready_counts": dict(sorted(cross_source_ready_counts.items())),
        "input_mode_counts": dict(sorted(input_mode_counts.items())),
        "snapshot_origin_counts": dict(sorted(snapshot_origin_counts.items())),
        "offline_ready_source_count": offline_ready_counts.get("ready", 0),
        "cross_source_ready_source_count": cross_source_ready_counts.get("ready", 0),
        "missing_reference_source_count": offline_ready_counts.get(
            "missing_references", 0
        ),
        "no_balance_target_source_count": offline_ready_counts.get(
            "no_balance_targets", 0
        ),
        "no_balance_input_source_count": offline_ready_counts.get(
            "no_balance_inputs", 0
        ),
        "missing_location_inventory_source_count": cross_source_ready_counts.get(
            "missing_location_inventory", 0
        ),
        "not_comparable_source_count": cross_source_ready_counts.get(
            "not_comparable", 0
        ),
        "not_applicable_source_count": cross_source_ready_counts.get(
            "not_applicable", 0
        ),
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
