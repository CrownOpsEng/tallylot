"""Archive-aware source intake planning and apply services."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from crypto_reconciliation.application.dtos import (
    IntakeApplyRequest,
    IntakeApplyResponse,
    IntakePlanRequest,
    IntakePlanResponse,
)
from crypto_reconciliation.application.services.archive_scan import ScannedFile, scanned_tree_files
from crypto_reconciliation.application.services.intake_packages import (
    PlannedPackageItem,
    apply_package_rules,
)
from crypto_reconciliation.application.services.intake_routing import route_intake_file
from crypto_reconciliation.ports.artifacts import ArtifactStorePort

PLAN_HEADER = (
    "path",
    "archive_source_path",
    "archive_member_path",
    "category",
    "role",
    "source_folder",
    "capture_id",
    "action",
    "package_key",
    "package_status",
    "placement_status",
    "review_required",
    "review_codes",
    "review_reason",
    "inventory_match_status",
    "target_path",
)
ISSUE_HEADER = ("relative_path", "severity", "kind", "message")


@dataclass(frozen=True)
class _PlannedItem:
    source_path: Path
    archive_source_path: str
    archive_member_path: str
    category: str
    role: str
    source_folder: str
    capture_id: str
    action: str
    package_key: str
    package_status: str
    placement_status: str
    review_required: str
    review_codes: str
    review_reason: str
    inventory_match_status: str
    sha256: str
    target_path: Path

    def to_row(self) -> dict[str, str]:
        return {
            "path": str(self.source_path),
            "archive_source_path": self.archive_source_path,
            "archive_member_path": self.archive_member_path,
            "category": self.category,
            "role": self.role,
            "source_folder": self.source_folder,
            "capture_id": self.capture_id,
            "action": self.action,
            "package_key": self.package_key,
            "package_status": self.package_status,
            "placement_status": self.placement_status,
            "review_required": self.review_required,
            "review_codes": self.review_codes,
            "review_reason": self.review_reason,
            "inventory_match_status": self.inventory_match_status,
            "target_path": str(self.target_path),
        }


class SourceIntakeService:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def plan(self, request: IntakePlanRequest) -> IntakePlanResponse:
        planned_items, issue_rows = self._plan_rows(request)
        self._write_reports(request.report_dir, planned_items, issue_rows, copied_count=0)
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
            planned_items = _build_planned_items(
                scanned_tree.files,
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
        self._write_reports(request.report_dir, planned_items, issue_rows, copied_count=copied_count)
        return IntakeApplyResponse(
            report_dir=request.report_dir,
            file_count=len(planned_items),
            issue_count=len(issue_rows),
            copied_count=copied_count,
        )

    def _plan_rows(
        self,
        request: IntakePlanRequest,
    ) -> tuple[list[_PlannedItem], list[dict[str, str]]]:
        request.report_dir.mkdir(parents=True, exist_ok=True)
        source_root = (
            request.workspace_root / "evidence" / "raw" / "source" / "unclassified" / request.incoming_dir.name
        )
        planned_items: list[_PlannedItem] = []
        issue_rows: list[dict[str, str]] = []
        with scanned_tree_files(
            request.incoming_dir,
            inspect_archives=request.inspect_archives,
        ) as scanned_tree:
            del source_root
            planned_items.extend(_build_planned_items(scanned_tree.files, request))
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

    def _write_reports(
        self,
        report_dir: Path,
        planned_items: list[_PlannedItem],
        issue_rows: list[dict[str, str]],
        *,
        copied_count: int,
    ) -> None:
        self._artifacts.write_rows(
            report_dir / "intake_plan.csv",
            PLAN_HEADER,
            (item.to_row() for item in planned_items),
        )
        self._artifacts.write_rows(report_dir / "intake_issues.csv", ISSUE_HEADER, issue_rows)
        self._artifacts.write_json(
            report_dir / "intake_summary.json",
            {
                "file_count": len(planned_items),
                "issue_count": len(issue_rows),
                "copied_count": copied_count,
                "planned_copy_count": sum(1 for item in planned_items if item.action in {"copy", "extract_copy"}),
                "duplicate_packages": sum(
                    1 for item in planned_items if item.package_status == "duplicate_package_subset"
                ),
            },
        )


def _build_planned_items(
    files: tuple[ScannedFile, ...],
    request: IntakePlanRequest,
) -> list[_PlannedItem]:
    planned_items: list[_PlannedItem] = []
    for entry in files:
        route = route_intake_file(
            entry,
            incoming_dir=request.incoming_dir,
            workspace_root=request.workspace_root,
        )
        planned_items.append(
            _PlannedItem(
                source_path=entry.file_path,
                archive_source_path=entry.archive_source_path,
                archive_member_path=entry.archive_member_path,
                category=route.category,
                role=route.role,
                source_folder=route.source_folder,
                capture_id=route.capture_id,
                action=route.action,
                package_key=_package_key(entry),
                package_status="primary",
                placement_status="planned_copy" if route.action in {"copy", "extract_copy"} else "inspect_only",
                review_required=route.review_required,
                review_codes=route.review_codes,
                review_reason=route.review_reason,
                inventory_match_status=route.inventory_match_status,
                sha256=entry.sha256,
                target_path=route.target_path,
            )
        )
    package_items = [
        PlannedPackageItem(
            path=str(item.source_path),
            source_folder=item.source_folder,
            category=item.category,
            action=item.action,
            sha256=item.sha256,
            package_key=item.package_key,
            package_status=item.package_status,
            placement_status=item.placement_status,
        )
        for item in planned_items
    ]
    updated_package_items, _ = apply_package_rules(package_items)
    package_map = {item.path: item for item in updated_package_items}
    return [
        _PlannedItem(
            source_path=item.source_path,
            archive_source_path=item.archive_source_path,
            archive_member_path=item.archive_member_path,
            category=item.category,
            role=item.role,
            source_folder=item.source_folder,
            capture_id=item.capture_id,
            action=package_map[str(item.source_path)].action,
            package_key=item.package_key,
            package_status=package_map[str(item.source_path)].package_status,
            placement_status=package_map[str(item.source_path)].placement_status,
            review_required=item.review_required,
            review_codes=item.review_codes,
            review_reason=item.review_reason,
            inventory_match_status=item.inventory_match_status,
            sha256=item.sha256,
            target_path=item.target_path,
        )
        for item in planned_items
    ]


def _package_key(entry: ScannedFile) -> str:
    if entry.archive_source_path:
        return entry.archive_source_path
    relative_path = Path(entry.relative_path)
    return str(relative_path.parent) if relative_path.parent != Path() else entry.relative_path
