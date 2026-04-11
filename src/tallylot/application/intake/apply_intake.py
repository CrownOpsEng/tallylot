"""Apply intake actions for incoming evidence."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from tallylot.application.intake.archive import scanned_tree_files
from tallylot.application.intake.captures.persistence import (
    CaptureRecordWrite,
    CaptureMetadataWrite,
    append_capture_record,
    update_source_inventory_summary,
    write_capture_metadata,
)
from tallylot.application.intake.contracts import (
    IntakeApplyRequest,
    IntakeApplyResponse,
    IntakePlanRequest,
)
from tallylot.application.intake.plan import (
    IntakeReportBundle,
    build_planned_items,
    write_capture_manifests,
    write_reports,
)
from tallylot.application.intake.plan.models import CaptureSessionPlan
from tallylot.application.resource_refs import path_from_ref
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.source_adapters import SourceAdapterRegistryPort


class ApplyIntakeUseCase:
    def __init__(
        self, registry: SourceAdapterRegistryPort, artifacts: ArtifactStorePort
    ) -> None:
        self._registry = registry
        self._artifacts = artifacts

    def execute(self, request: IntakeApplyRequest) -> IntakeApplyResponse:
        incoming_dir = path_from_ref(request.incoming_capture_ref)
        workspace_root = path_from_ref(request.workspace_root_ref)
        report_dir = path_from_ref(request.report_output_ref)
        report_dir.mkdir(parents=True, exist_ok=True)
        copied_count = 0
        intake_started_at = datetime.now(UTC)
        incoming_ref = _incoming_ref(
            request.incoming_capture_ref, incoming_dir, workspace_root
        )
        capture_metadata = None
        capture_session_plan: CaptureSessionPlan | None = None
        with scanned_tree_files(
            incoming_dir, inspect_archives=request.inspect_archives
        ) as scanned_tree:
            batch = build_planned_items(
                scanned_tree.files,
                self._registry,
                self._artifacts,
                IntakePlanRequest(
                    incoming_capture_ref=request.incoming_capture_ref,
                    workspace_root_ref=request.workspace_root_ref,
                    report_output_ref=request.report_output_ref,
                    inspect_archives=request.inspect_archives,
                ),
            )
            planned_items = list(batch.planned_items)
            issue_rows = list(batch.issue_rows)
            issue_rows.extend(
                {
                    "relative_path": issue.relative_path,
                    "severity": issue.severity,
                    "kind": issue.kind,
                    "message": issue.message,
                }
                for issue in scanned_tree.issues
            )
            capture_session_plan = batch.capture_session_plan
            materializes_capture = _session_materializes_capture(
                capture_session_plan.capture_status
            )
            for item in planned_items:
                if item.action not in {"copy", "extract_copy"}:
                    continue
                if item.category == "source_raw" and not materializes_capture:
                    continue
                item.target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item.source_path, item.target_path)
                copied_count += 1
            if materializes_capture:
                write_capture_manifests(self._artifacts, workspace_root, planned_items)
        assert capture_session_plan is not None
        should_record_capture = bool(capture_session_plan.source_folder)
        materialized_capture = _session_materializes_capture(
            capture_session_plan.capture_status
        )
        if capture_session_plan.source_folder and _session_materializes_capture(
            capture_session_plan.capture_status
        ):
            capture_root = (
                workspace_root
                / "evidence"
                / "raw"
                / "source"
                / capture_session_plan.source_folder
                / capture_session_plan.capture_label
            )
            intake_completed_at = datetime.now(UTC)
            capture_metadata = write_capture_metadata(
                artifacts=self._artifacts,
                write=CaptureMetadataWrite(
                    capture_root=capture_root,
                    source=capture_session_plan.source_folder,
                    capture_label=capture_session_plan.capture_label,
                    intake_started_at=intake_started_at,
                    intake_completed_at=intake_completed_at,
                    incoming_ref=incoming_ref,
                    manifest_fingerprint=capture_session_plan.manifest_fingerprint,
                    status="captured"
                    if capture_session_plan.capture_status == "planned"
                    else capture_session_plan.capture_status,
                ),
            )
        if should_record_capture:
            append_capture_record(
                artifacts=self._artifacts,
                write=CaptureRecordWrite(
                    workspace_root=workspace_root,
                    metadata=capture_metadata,
                    plan=capture_session_plan,
                    capture_root_ref=(
                        f"evidence/raw/source/{capture_session_plan.source_folder}/{capture_session_plan.capture_label}"
                        if materialized_capture
                        else ""
                    ),
                    intake_started_at=intake_started_at,
                    intake_completed_at=datetime.now(UTC),
                    incoming_ref=incoming_ref,
                ),
            )
        if should_record_capture and _session_updates_source_inventory(
            capture_session_plan.capture_status
        ):
            update_source_inventory_summary(
                artifacts=self._artifacts,
                workspace_root=workspace_root,
                source=capture_session_plan.source_folder,
                assembled_output_present=(
                    False if capture_session_plan.capture_status == "planned" else None
                ),
                assembly_excluded_capture_count=(
                    0 if capture_session_plan.capture_status == "planned" else None
                ),
            )
        summary_capture_status = (
            capture_metadata.status
            if capture_metadata is not None
            else capture_session_plan.capture_status
        )
        write_reports(
            self._artifacts,
            report_dir,
            IntakeReportBundle(
                planned_items=planned_items,
                issue_rows=issue_rows,
                capture_session_plan=capture_session_plan,
                copied_count=copied_count,
                summary_capture_status=summary_capture_status,
            ),
        )
        return IntakeApplyResponse(
            report_output_ref=request.report_output_ref,
            source=(
                str(capture_metadata.source)
                if capture_metadata is not None
                else capture_session_plan.source_folder
            ),
            capture_status=(
                capture_metadata.status
                if capture_metadata is not None
                else capture_session_plan.capture_status
            ),
            capture_label=(
                capture_metadata.capture_label
                if capture_metadata is not None
                else capture_session_plan.capture_label
                if materialized_capture
                else ""
            ),
            file_count=len(planned_items),
            issue_count=len(issue_rows),
            copied_count=copied_count,
        )


def _incoming_ref(
    incoming_capture_ref: str, incoming_dir: Path, workspace_root: Path
) -> str:
    ref_path = Path(incoming_capture_ref)
    if not ref_path.is_absolute():
        return ref_path.as_posix()
    try:
        return incoming_dir.relative_to(workspace_root).as_posix()
    except ValueError:
        return f"incoming/{incoming_dir.name}"


def _session_materializes_capture(capture_status: str) -> bool:
    return capture_status not in {"capture_blocked", "duplicate_blocked"}


def _session_updates_source_inventory(capture_status: str) -> bool:
    return capture_status != "capture_blocked"
