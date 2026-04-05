"""Apply intake actions for incoming evidence."""

from __future__ import annotations

import shutil

from tallylot.application.intake.archive import scanned_tree_files
from tallylot.application.intake.contracts import (
    IntakeApplyRequest,
    IntakeApplyResponse,
    IntakePlanRequest,
)
from tallylot.application.intake.plan import (
    build_planned_items,
    write_capture_manifests,
    write_reports,
)
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
            for item in planned_items:
                if item.action not in {"copy", "extract_copy"}:
                    continue
                item.target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item.source_path, item.target_path)
                copied_count += 1
            write_capture_manifests(self._artifacts, workspace_root, planned_items)
        write_reports(
            self._artifacts,
            report_dir,
            planned_items,
            issue_rows,
            copied_count=copied_count,
        )
        return IntakeApplyResponse(
            report_output_ref=request.report_output_ref,
            file_count=len(planned_items),
            issue_count=len(issue_rows),
            copied_count=copied_count,
        )
