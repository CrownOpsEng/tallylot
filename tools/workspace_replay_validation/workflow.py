from __future__ import annotations

import csv
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from tallylot.application.intake.contracts import (
    IntakeApplyRequest,
    IntakePlanRequest,
    ManifestRequest,
)
from tallylot.application.capture_paths import (
    default_capture_normalized_root,
)
from tallylot.application.normalization.contracts import (
    AssembleSourceRequest,
    NormalizeRequest,
)
from tallylot.application.profiling.contracts import ProfileRequest
from tallylot.application.resource_refs import to_resource_ref, to_workspace_path
from tallylot.application.workspace.contracts import WorkspaceInitRequest
from tallylot.infrastructure.composition.runtime import (
    apply_intake_use_case,
    assemble_source_use_case,
    build_manifest_use_case,
    build_profile_use_case,
    initialize_workspace_use_case,
    normalize_source_use_case,
    plan_intake_use_case,
)
from tallylot.infrastructure.serialization import FilesystemArtifactStore
from tallylot.ports.captures import CaptureMetadata, SOURCE_INVENTORY_HEADER

from .comparison import collect_workspace_metrics, write_parity_report
from .expected_differences import load_expected_differences
from .models import (
    MetricCollectionRequest,
    ParityReportRequest,
    ReferenceCapture,
    ReplayResult,
    WorkspaceReplayValidationRequest,
)


def _latest_capture_rows(rows: list[dict[str, str]]) -> tuple[dict[str, str], ...]:
    latest_by_uid: dict[str, dict[str, str]] = {}
    for row in rows:
        capture_uid = row.get("capture_uid", "").strip()
        if capture_uid:
            latest_by_uid[capture_uid] = row
    return tuple(
        latest_by_uid[capture_uid]
        for capture_uid in sorted(
            latest_by_uid,
            key=lambda value: (
                _parse_optional_timestamp(
                    latest_by_uid[value].get("intake_completed_at", "")
                )
                or datetime.min.replace(tzinfo=UTC),
                latest_by_uid[value].get("source", ""),
                latest_by_uid[value].get("capture_label", ""),
                value,
            ),
        )
    )


def _parse_optional_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)


def _reference_captures(
    *,
    artifacts: FilesystemArtifactStore,
    workspace_root: Path,
    selected_sources: frozenset[str],
) -> tuple[ReferenceCapture, ...]:
    capture_registry_path = (
        workspace_root / "analysis" / "inventory" / "source_captures.csv"
    )
    rows = (
        artifacts.read_rows(capture_registry_path)
        if capture_registry_path.is_file()
        else []
    )
    captures: list[ReferenceCapture] = []
    for index, row in enumerate(_latest_capture_rows(rows), start=1):
        source = row.get("source", "").strip()
        if not source or (selected_sources and source not in selected_sources):
            continue
        manifest_fingerprint = row.get("manifest_fingerprint", "").strip()
        if not manifest_fingerprint:
            continue
        raw_capture_root = _resolve_capture_root(workspace_root, row)
        if raw_capture_root is None or not raw_capture_root.is_dir():
            continue
        captures.append(
            ReferenceCapture(
                source=source,
                manifest_fingerprint=manifest_fingerprint,
                raw_capture_root=raw_capture_root,
                report_slug=f"{index:03d}_{source}",
            )
        )
    if not captures:
        raise ValueError(
            "reference workspace did not expose any materialized raw captures"
        )
    return tuple(captures)


def _resolve_capture_root(
    workspace_root: Path,
    row: dict[str, str],
) -> Path | None:
    capture_root_ref = row.get("capture_root_ref", "").strip()
    if capture_root_ref:
        return workspace_root / Path(capture_root_ref)
    return None


def _seed_candidate_workspace(
    *,
    artifacts: FilesystemArtifactStore,
    reference_workspace: Path,
    candidate_workspace: Path,
    captures: tuple[ReferenceCapture, ...],
) -> None:
    initialize_workspace_use_case().execute(
        WorkspaceInitRequest(workspace_root_ref=to_workspace_path(candidate_workspace))
    )
    reference_inventory_path = (
        reference_workspace / "analysis" / "issues" / "source_inventory.csv"
    )
    reference_map_path = (
        reference_workspace / "analysis" / "issues" / "source_label_map.csv"
    )
    needed_sources = {capture.source for capture in captures}
    inventory_rows = (
        artifacts.read_rows(reference_inventory_path)
        if reference_inventory_path.is_file()
        else []
    )
    seeded_rows = [
        {
            "source": row.get("source", ""),
            "activity_after_cutoff": row.get("activity_after_cutoff", ""),
            "scope_status": row.get("scope_status", ""),
            "status": "",
            "capture_count": "",
            "latest_capture_uid": "",
            "latest_capture_label": "",
            "latest_capture_completed_at": "",
            "assembly_status": "",
            "assembled_root_ref": "",
            "adapter_hints": row.get("adapter_hints", ""),
            "notes": row.get("notes", ""),
        }
        for row in inventory_rows
        if row.get("source", "") in needed_sources
    ]
    missing_sources = sorted(
        needed_sources - {row.get("source", "") for row in seeded_rows}
    )
    seeded_rows.extend(
        {
            "source": source,
            "activity_after_cutoff": "",
            "scope_status": "",
            "status": "",
            "capture_count": "",
            "latest_capture_uid": "",
            "latest_capture_label": "",
            "latest_capture_completed_at": "",
            "assembly_status": "",
            "assembled_root_ref": "",
            "adapter_hints": "",
            "notes": "",
        }
        for source in missing_sources
    )
    artifacts.write_rows(
        candidate_workspace / "analysis" / "issues" / "source_inventory.csv",
        SOURCE_INVENTORY_HEADER,
        seeded_rows,
    )
    _seed_source_label_map(
        reference_map_path=reference_map_path,
        candidate_workspace=candidate_workspace,
        needed_sources=needed_sources,
        captures=captures,
    )


def _seed_source_label_map(
    *,
    reference_map_path: Path,
    candidate_workspace: Path,
    needed_sources: set[str],
    captures: tuple[ReferenceCapture, ...],
) -> None:
    filtered_rows: list[dict[str, str]] = []
    fieldnames: tuple[str, ...] = (
        "incoming_capture_scope",
        "incoming_path_prefix",
        "source",
        "notes",
    )
    if reference_map_path.is_file():
        with reference_map_path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is not None:
                fieldnames = _source_label_map_fieldnames(tuple(reader.fieldnames))
                filtered_rows = [
                    {field_name: row.get(field_name, "") for field_name in fieldnames}
                    for row in reader
                    if (row.get("source") or "").strip() in needed_sources
                ]
    filtered_rows.extend(
        {
            "incoming_capture_scope": capture.report_slug,
            "incoming_path_prefix": ".",
            "source": capture.source,
            "notes": "workspace replay staged capture scope",
        }
        for capture in captures
    )
    target_path = candidate_workspace / "analysis" / "issues" / "source_label_map.csv"
    with target_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered_rows)


def _source_label_map_fieldnames(
    fieldnames: tuple[str, ...],
) -> tuple[str, ...]:
    ordered = list(fieldnames)
    for required in (
        "incoming_capture_scope",
        "incoming_path_prefix",
        "source",
        "notes",
    ):
        if required not in ordered:
            insert_at = 0 if required == "incoming_capture_scope" else len(ordered)
            ordered.insert(insert_at, required)
    return tuple(ordered)


def _copy_replay_inputs(
    reference_capture_root: Path, staged_capture_root: Path
) -> None:
    for source_path in sorted(reference_capture_root.rglob("*")):
        if source_path.is_dir():
            continue
        relative_path = source_path.relative_to(reference_capture_root)
        if relative_path.as_posix() in {
            "capture.json",
            "manifest.csv",
            "manifest_issues.csv",
        }:
            continue
        target_path = staged_capture_root / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def _replay_capture(
    *,
    candidate_workspace: Path,
    report_dir: Path,
    capture: ReferenceCapture,
    inspect_archives: bool,
) -> None:
    staged_capture_root = report_dir / "staged_captures" / capture.report_slug
    replay_report_dir = report_dir / "replay" / capture.report_slug
    _copy_replay_inputs(capture.raw_capture_root, staged_capture_root)
    plan_intake_use_case().execute(
        IntakePlanRequest(
            incoming_capture_ref=to_resource_ref(staged_capture_root),
            workspace_root_ref=to_workspace_path(candidate_workspace),
            report_output_ref=to_resource_ref(replay_report_dir),
            inspect_archives=inspect_archives,
        )
    )
    apply_intake_use_case().execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(staged_capture_root),
            workspace_root_ref=to_workspace_path(candidate_workspace),
            report_output_ref=to_resource_ref(replay_report_dir),
            inspect_archives=inspect_archives,
        )
    )
    summary = json.loads(
        (replay_report_dir / "intake_summary.json").read_text(encoding="utf-8")
    )
    if summary.get("capture_status") == "capture_blocked":
        raise ValueError(
            "workspace replay intake apply did not materialize a capture; "
            f"see {replay_report_dir / 'intake_issues.csv'}"
        )
    capture_label = str(summary["planned_capture_label"])
    raw_capture_root = (
        candidate_workspace
        / "evidence"
        / "raw"
        / "source"
        / capture.source
        / capture_label
    )
    build_manifest_use_case().execute(
        ManifestRequest(
            source_capture_ref=to_resource_ref(raw_capture_root),
            manifest_output_ref=to_resource_ref(replay_report_dir / "manifest.csv"),
            inspect_archives=inspect_archives,
        )
    )
    metadata = CaptureMetadata.from_dict(
        json.loads((raw_capture_root / "capture.json").read_text(encoding="utf-8"))
    )
    normalized_output = default_capture_normalized_root(raw_capture_root)
    build_profile_use_case().execute(
        ProfileRequest(
            source=capture.source,
            raw_capture_ref=to_resource_ref(raw_capture_root),
            profile_output_ref=to_resource_ref(normalized_output),
            inspect_archives=inspect_archives,
        )
    )
    normalize_source_use_case().execute(
        NormalizeRequest(
            source=capture.source,
            raw_capture_ref=to_resource_ref(raw_capture_root),
            normalized_output_ref=to_resource_ref(normalized_output),
            inspect_archives=inspect_archives,
        )
    )
    replay_report_dir.joinpath("capture_uid.txt").write_text(
        str(metadata.capture_uid),
        encoding="utf-8",
    )


def _validate_reference_sources_ready(
    *,
    workspace_root: Path,
    captures: tuple[ReferenceCapture, ...],
) -> None:
    for source in sorted({capture.source for capture in captures}):
        assembly_summary_path = (
            workspace_root
            / "working"
            / "normalized"
            / "sources"
            / source
            / "assembly_summary.json"
        )
        if not assembly_summary_path.is_file():
            raise ValueError(
                "reference workspace is missing an assembled source summary for "
                f"{source}: {assembly_summary_path}"
            )
        payload = json.loads(assembly_summary_path.read_text(encoding="utf-8"))
        pending_capture_count = payload.get("pending_capture_count", 0)
        if not isinstance(pending_capture_count, int):
            raise ValueError(
                "reference workspace assembly summary contains a non-integer "
                f"pending_capture_count for {source}: {assembly_summary_path}"
            )
        if pending_capture_count:
            raise ValueError(
                "reference workspace source is not replay-ready because it still "
                f"has {pending_capture_count} pending captures: {source}"
            )


def validate_workspace_replay(
    request: WorkspaceReplayValidationRequest,
) -> ReplayResult:
    artifacts = FilesystemArtifactStore()
    expected_differences = load_expected_differences(
        request.expected_differences_path
    ).limited_to_sources(request.selected_sources)
    captures = _reference_captures(
        artifacts=artifacts,
        workspace_root=request.reference_workspace,
        selected_sources=request.selected_sources,
    )
    _validate_reference_sources_ready(
        workspace_root=request.reference_workspace,
        captures=captures,
    )
    _seed_candidate_workspace(
        artifacts=artifacts,
        reference_workspace=request.reference_workspace,
        candidate_workspace=request.candidate_workspace,
        captures=captures,
    )
    for capture in captures:
        _replay_capture(
            candidate_workspace=request.candidate_workspace,
            report_dir=request.report_dir,
            capture=capture,
            inspect_archives=request.inspect_archives,
        )
    for source in sorted({capture.source for capture in captures}):
        assemble_source_use_case().execute(
            AssembleSourceRequest(
                source=source,
                workspace_root_ref=to_resource_ref(request.candidate_workspace),
            )
        )
    reference_metrics = collect_workspace_metrics(
        MetricCollectionRequest(
            artifacts=artifacts,
            workspace_root=request.reference_workspace,
            selected_sources=request.selected_sources,
            reconciliation_report_dir=request.report_dir / "reference",
            latest_capture_rows=_latest_capture_rows(
                artifacts.read_rows(
                    request.reference_workspace
                    / "analysis"
                    / "inventory"
                    / "source_captures.csv"
                )
            ),
            resolve_capture_root=_resolve_capture_root,
        )
    )
    candidate_metrics = collect_workspace_metrics(
        MetricCollectionRequest(
            artifacts=artifacts,
            workspace_root=request.candidate_workspace,
            selected_sources=request.selected_sources,
            reconciliation_report_dir=request.report_dir / "candidate",
            latest_capture_rows=_latest_capture_rows(
                artifacts.read_rows(
                    request.candidate_workspace
                    / "analysis"
                    / "inventory"
                    / "source_captures.csv"
                )
            ),
            resolve_capture_root=_resolve_capture_root,
        )
    )
    return write_parity_report(
        ParityReportRequest(
            artifacts=artifacts,
            report_dir=request.report_dir,
            reference_workspace=request.reference_workspace,
            candidate_workspace=request.candidate_workspace,
            reference_metrics=reference_metrics,
            candidate_metrics=candidate_metrics,
            expected_differences=expected_differences,
        )
    )


__all__ = [
    "validate_workspace_replay",
    "_reference_captures",
    "_validate_reference_sources_ready",
]
