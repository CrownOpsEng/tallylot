"""Plan intake actions for incoming evidence."""

from __future__ import annotations

from tallylot.application.intake.archive import scanned_tree_files
from tallylot.application.intake.contracts import IntakePlanRequest, IntakePlanResponse
from tallylot.application.intake.plan import (
    IntakeReportBundle,
    build_planned_items,
    write_reports,
)
from tallylot.application.resource_refs import path_from_ref
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.source_adapters import SourceAdapterRegistryPort


class PlanIntakeUseCase:
    def __init__(
        self, registry: SourceAdapterRegistryPort, artifacts: ArtifactStorePort
    ) -> None:
        self._registry = registry
        self._artifacts = artifacts

    def execute(self, request: IntakePlanRequest) -> IntakePlanResponse:
        incoming_dir = path_from_ref(request.incoming_capture_ref)
        report_dir = path_from_ref(request.report_output_ref)
        report_dir.mkdir(parents=True, exist_ok=True)
        issue_rows: list[dict[str, str]] = []
        with scanned_tree_files(
            incoming_dir, inspect_archives=request.inspect_archives
        ) as scanned_tree:
            batch = build_planned_items(
                scanned_tree.files, self._registry, self._artifacts, request
            )
            planned_items = list(batch.planned_items)
            issue_rows.extend(batch.issue_rows)
            issue_rows.extend(
                {
                    "relative_path": issue.relative_path,
                    "severity": issue.severity,
                    "kind": issue.kind,
                    "message": issue.message,
                }
                for issue in scanned_tree.issues
            )
        write_reports(
            self._artifacts,
            report_dir,
            IntakeReportBundle(
                planned_items=planned_items,
                issue_rows=issue_rows,
                capture_session_plan=batch.capture_session_plan,
                copied_count=0,
            ),
        )
        return IntakePlanResponse(
            report_output_ref=request.report_output_ref,
            file_count=len(planned_items),
            issue_count=len(issue_rows),
            planned_copy_count=sum(
                1 for item in planned_items if item.action in {"copy", "extract_copy"}
            ),
        )
