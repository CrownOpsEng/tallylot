"""Plan intake actions for incoming evidence."""

from __future__ import annotations

from crypto_reconciliation.application.intake.archive import scanned_tree_files
from crypto_reconciliation.application.intake.contracts import IntakePlanRequest, IntakePlanResponse
from crypto_reconciliation.application.intake.plan import PlannedItem, build_planned_items, write_reports
from crypto_reconciliation.ports.artifacts import ArtifactStorePort
from crypto_reconciliation.ports.source_adapters import SourceAdapterRegistryPort


class PlanIntakeUseCase:
    def __init__(self, registry: SourceAdapterRegistryPort, artifacts: ArtifactStorePort) -> None:
        self._registry = registry
        self._artifacts = artifacts

    def execute(self, request: IntakePlanRequest) -> IntakePlanResponse:
        request.report_dir.mkdir(parents=True, exist_ok=True)
        planned_items: list[PlannedItem] = []
        issue_rows: list[dict[str, str]] = []
        with scanned_tree_files(request.incoming_dir, inspect_archives=request.inspect_archives) as scanned_tree:
            planned_items.extend(build_planned_items(scanned_tree.files, self._registry, self._artifacts, request))
            issue_rows.extend(
                {
                    "relative_path": issue.relative_path,
                    "severity": issue.severity,
                    "kind": issue.kind,
                    "message": issue.message,
                }
                for issue in scanned_tree.issues
            )
        write_reports(self._artifacts, request.report_dir, planned_items, issue_rows, copied_count=0)
        return IntakePlanResponse(
            report_dir=request.report_dir,
            file_count=len(planned_items),
            issue_count=len(issue_rows),
            planned_copy_count=sum(1 for item in planned_items if item.action in {"copy", "extract_copy"}),
        )
