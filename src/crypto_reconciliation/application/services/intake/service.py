"""Archive-aware source intake planning and apply services."""

from __future__ import annotations

import shutil

from crypto_reconciliation.application.dtos import (
    IntakeApplyRequest,
    IntakeApplyResponse,
    IntakePlanRequest,
    IntakePlanResponse,
)
from crypto_reconciliation.ports.artifacts import ArtifactStorePort

from .archive import scanned_tree_files
from .plan_builder import build_planned_items
from .plan_models import PlannedItem
from .plan_reports import write_capture_manifests, write_reports


class SourceIntakeService:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def plan(self, request: IntakePlanRequest) -> IntakePlanResponse:
        planned_items, issue_rows = self._plan_rows(request)
        write_reports(self._artifacts, request.report_dir, planned_items, issue_rows, copied_count=0)
        return IntakePlanResponse(
            report_dir=request.report_dir,
            file_count=len(planned_items),
            issue_count=len(issue_rows),
            planned_copy_count=sum(1 for item in planned_items if item.action in {"copy", "extract_copy"}),
        )

    def apply(self, request: IntakeApplyRequest) -> IntakeApplyResponse:
        request.report_dir.mkdir(parents=True, exist_ok=True)
        copied_count = 0
        with scanned_tree_files(
            request.incoming_dir,
            inspect_archives=request.inspect_archives,
        ) as scanned_tree:
            planned_items = build_planned_items(
                scanned_tree.files,
                self._artifacts,
                IntakePlanRequest(
                    incoming_dir=request.incoming_dir,
                    workspace_root=request.workspace_root,
                    report_dir=request.report_dir,
                    inspect_archives=request.inspect_archives,
                ),
            )
            issue_rows = [
                {
                    "relative_path": issue.relative_path,
                    "severity": issue.severity,
                    "kind": issue.kind,
                    "message": issue.message,
                }
                for issue in scanned_tree.issues
            ]
            for item in planned_items:
                if item.action not in {"copy", "extract_copy"}:
                    continue
                item.target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item.source_path, item.target_path)
                copied_count += 1
            write_capture_manifests(self._artifacts, request.workspace_root, planned_items)
        write_reports(self._artifacts, request.report_dir, planned_items, issue_rows, copied_count=copied_count)
        return IntakeApplyResponse(
            report_dir=request.report_dir,
            file_count=len(planned_items),
            issue_count=len(issue_rows),
            copied_count=copied_count,
        )

    def _plan_rows(
        self,
        request: IntakePlanRequest,
    ) -> tuple[list[PlannedItem], list[dict[str, str]]]:
        request.report_dir.mkdir(parents=True, exist_ok=True)
        planned_items: list[PlannedItem] = []
        issue_rows: list[dict[str, str]] = []
        with scanned_tree_files(
            request.incoming_dir,
            inspect_archives=request.inspect_archives,
        ) as scanned_tree:
            planned_items.extend(build_planned_items(scanned_tree.files, self._artifacts, request))
            issue_rows.extend(
                {
                    "relative_path": issue.relative_path,
                    "severity": issue.severity,
                    "kind": issue.kind,
                    "message": issue.message,
                }
                for issue in scanned_tree.issues
            )
        return planned_items, issue_rows
