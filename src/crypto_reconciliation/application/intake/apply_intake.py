"""Apply intake actions for incoming evidence."""

from __future__ import annotations

import shutil

from crypto_reconciliation.application.intake.archive import scanned_tree_files
from crypto_reconciliation.application.intake.contracts import (
    IntakeApplyRequest,
    IntakeApplyResponse,
    IntakePlanRequest,
)
from crypto_reconciliation.application.intake.plan import (
    build_planned_items,
    write_capture_manifests,
    write_reports,
)
from crypto_reconciliation.ports.artifacts import ArtifactStorePort
from crypto_reconciliation.ports.source_adapters import SourceAdapterRegistryPort


class ApplyIntakeUseCase:
    def __init__(self, registry: SourceAdapterRegistryPort, artifacts: ArtifactStorePort) -> None:
        self._registry = registry
        self._artifacts = artifacts

    def execute(self, request: IntakeApplyRequest) -> IntakeApplyResponse:
        request.report_dir.mkdir(parents=True, exist_ok=True)
        copied_count = 0
        with scanned_tree_files(request.incoming_dir, inspect_archives=request.inspect_archives) as scanned_tree:
            planned_items = build_planned_items(
                scanned_tree.files,
                self._registry,
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
