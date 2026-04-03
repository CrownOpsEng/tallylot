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
from crypto_reconciliation.application.services.archive_scan import scanned_tree_files
from crypto_reconciliation.ports.artifacts import ArtifactStorePort

PLAN_HEADER = (
    "path",
    "archive_source_path",
    "archive_member_path",
    "category",
    "action",
    "target_path",
)
ISSUE_HEADER = ("relative_path", "severity", "kind", "message")


@dataclass(frozen=True)
class _PlannedItem:
    source_path: Path
    archive_source_path: str
    archive_member_path: str
    category: str
    action: str
    target_path: Path

    def to_row(self) -> dict[str, str]:
        return {
            "path": str(self.source_path),
            "archive_source_path": self.archive_source_path,
            "archive_member_path": self.archive_member_path,
            "category": self.category,
            "action": self.action,
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
            planned_copy_count=sum(1 for item in planned_items if item.action == "copy"),
        )

    def apply(self, request: IntakeApplyRequest) -> IntakeApplyResponse:
        planned_items, issue_rows = self._plan_rows(
            IntakePlanRequest(
                incoming_dir=request.incoming_dir,
                workspace_root=request.workspace_root,
                report_dir=request.report_dir,
                inspect_archives=request.inspect_archives,
            )
        )
        copied_count = 0
        for item in planned_items:
            if item.action != "copy":
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
        supporting_root = (
            request.workspace_root / "working" / "supporting_artifacts" / "intake" / request.incoming_dir.name
        )
        planned_items: list[_PlannedItem] = []
        issue_rows: list[dict[str, str]] = []
        with scanned_tree_files(
            request.incoming_dir,
            inspect_archives=request.inspect_archives,
        ) as scanned_tree:
            for entry in scanned_tree.files:
                category = "source_raw" if _is_source_raw(entry.relative_path) else "supporting_artifact"
                target_root = source_root if category == "source_raw" else supporting_root
                action = "inspect_only" if entry.archive_member_path else "copy"
                target_path = target_root / _relative_target_path(entry.relative_path)
                planned_items.append(
                    _PlannedItem(
                        source_path=entry.file_path,
                        archive_source_path=entry.archive_source_path,
                        archive_member_path=entry.archive_member_path,
                        category=category,
                        action=action,
                        target_path=target_path,
                    )
                )
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
                "planned_copy_count": sum(1 for item in planned_items if item.action == "copy"),
            },
        )


def _is_source_raw(relative_path: str) -> bool:
    suffix = Path(relative_path.replace("::", "__")).suffix.lower()
    return suffix in {".csv", ".json", ".zip"}


def _relative_target_path(relative_path: str) -> Path:
    return Path(relative_path.replace("::", "/members/"))
