"""Artifact writing for intake plans and apply runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tallylot.application.intake.captures.session import apply_capture_session_plan
from tallylot.application.intake.contracts import INTAKE_ISSUE_HEADER
from tallylot.ports.artifacts import ArtifactStorePort

from .models import (
    PLAN_HEADER,
    CaptureSessionPlan,
    CaptureSessionSummaryContext,
    PlannedItem,
)


@dataclass(frozen=True)
class IntakeReportBundle:
    planned_items: list[PlannedItem]
    issue_rows: list[dict[str, str]]
    capture_session_plan: CaptureSessionPlan
    copied_count: int
    summary_capture_status: str | None = None


def write_reports(
    artifacts: ArtifactStorePort,
    report_dir: Path,
    bundle: IntakeReportBundle,
) -> None:
    artifacts.write_rows(
        report_dir / "intake_plan.csv",
        PLAN_HEADER,
        (item.to_row() for item in bundle.planned_items),
    )
    artifacts.write_rows(
        report_dir / "intake_issues.csv", INTAKE_ISSUE_HEADER, bundle.issue_rows
    )
    apply_capture_session_plan(
        artifacts=artifacts,
        report_dir=report_dir,
        plan=bundle.capture_session_plan,
        context=CaptureSessionSummaryContext(
            planned_items=bundle.planned_items,
            issue_rows=bundle.issue_rows,
            copied_count=bundle.copied_count,
        ),
        summary_capture_status=bundle.summary_capture_status,
    )


def write_capture_manifests(
    artifacts: ArtifactStorePort,
    workspace_root: Path,
    planned_items: list[PlannedItem],
) -> None:
    capture_rows: dict[Path, list[dict[str, str]]] = {}
    for item in planned_items:
        if (
            item.category != "source_raw"
            or item.placement_status.startswith("package_")
            or item.action == "skip"
        ):
            continue
        capture_root = (
            workspace_root
            / "evidence"
            / "raw"
            / "source"
            / item.source_folder
            / item.capture_label
        )
        capture_rows.setdefault(capture_root, []).append(
            {
                "filename": str(item.target_path.relative_to(capture_root)),
                "sha256": item.sha256,
                "size_bytes": (
                    str(item.target_path.stat().st_size)
                    if item.target_path.exists()
                    else str(item.source_path.stat().st_size)
                ),
                "source_paths": str(item.source_path),
            }
        )
    for capture_root, rows in capture_rows.items():
        artifacts.write_rows(
            capture_root / "manifest.csv",
            ("filename", "sha256", "size_bytes", "source_paths"),
            rows,
        )
