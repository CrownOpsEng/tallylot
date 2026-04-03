"""Artifact writing for intake plans and apply runs."""

from __future__ import annotations

from pathlib import Path

from tallylot.ports.artifacts import ArtifactStorePort

from .models import ISSUE_HEADER, PLAN_HEADER, PlannedItem


def write_reports(
    artifacts: ArtifactStorePort,
    report_dir: Path,
    planned_items: list[PlannedItem],
    issue_rows: list[dict[str, str]],
    *,
    copied_count: int,
) -> None:
    artifacts.write_rows(
        report_dir / "intake_plan.csv",
        PLAN_HEADER,
        (item.to_row() for item in planned_items),
    )
    artifacts.write_rows(report_dir / "intake_issues.csv", ISSUE_HEADER, issue_rows)
    artifacts.write_json(
        report_dir / "intake_summary.json",
        {
            "file_count": len(planned_items),
            "issue_count": len(issue_rows),
            "copied_count": copied_count,
            "planned_copy_count": sum(1 for item in planned_items if item.action in {"copy", "extract_copy"}),
            "duplicate_packages": _package_count(planned_items, "duplicate_package"),
            "merge_primary_packages": _package_count(planned_items, "merge_primary"),
            "merged_packages": _package_count(planned_items, "merge_member"),
            "overlap_packages": _package_count(planned_items, "overlap_partial_review"),
            "mixed_cycle_packages": _package_count(planned_items, "mixed_cycle_review"),
        },
    )


def write_capture_manifests(
    artifacts: ArtifactStorePort,
    workspace_root: Path,
    planned_items: list[PlannedItem],
) -> None:
    capture_rows: dict[Path, list[dict[str, str]]] = {}
    for item in planned_items:
        if item.category != "source_raw" or item.placement_status.startswith("package_") or item.action == "skip":
            continue
        capture_root = workspace_root / "evidence" / "raw" / "source" / item.source_folder / item.capture_id
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


def _package_count(planned_items: list[PlannedItem], package_status: str) -> int:
    return len(
        {
            (item.source_folder, item.capture_id, item.bundle_id)
            for item in planned_items
            if item.package_status == package_status
            or (package_status == "duplicate_package" and item.package_status.startswith("duplicate_package"))
        }
    )
