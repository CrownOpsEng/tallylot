"""Capture-session planning for intake runs."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from tallylot.ports.artifacts import ArtifactStorePort

from ..contracts import IntakePlanRequest
from ..plan.models import CaptureSessionPlan, CaptureSessionSummaryContext, PlannedItem
from ...resource_refs import path_from_ref
from .capture_planning import (
    capture_blocked_plan,
    mark_mixed_source_capture_blocked,
    mark_missing_source_raw_capture_blocked,
    mark_non_materialized_capture_items,
    mark_source_raw_items_capture_blocked,
    manifest_fingerprint,
    overlaps,
    planned_capture_label,
    read_capture_rows,
    source_raw_target_path_for_item,
)


def build_capture_session_plan(
    *,
    planned_items: list[PlannedItem],
    artifacts: ArtifactStorePort,
    request: IntakePlanRequest,
    issue_rows: list[dict[str, str]],
) -> CaptureSessionPlan:
    report_dir = path_from_ref(request.report_output_ref)
    source_items = [item for item in planned_items if item.category == "source_raw"]
    raw_items = [
        item
        for item in planned_items
        if item.category == "source_raw" and item.action != "skip"
    ]
    distinct_sources = sorted(
        {item.source_folder for item in raw_items if item.source_folder}
    )
    if len(distinct_sources) > 1:
        issue_rows.append(
            {
                "relative_path": "",
                "severity": "high",
                "kind": "mixed_source_capture",
                "message": f"Intake run resolved multiple source folders: {', '.join(distinct_sources)}",
            }
        )
        mark_mixed_source_capture_blocked(planned_items)
        return capture_blocked_plan(file_count=len(source_items))
    if not raw_items:
        if source_items:
            mark_non_materialized_capture_items(
                planned_items,
                capture_status="capture_blocked",
                placement_status="capture_blocked_skip",
            )
            mark_source_raw_items_capture_blocked(planned_items)
        else:
            issue_rows.append(
                {
                    "relative_path": "",
                    "severity": "high",
                    "kind": "capture_missing_source_raw",
                    "message": (
                        "Intake run did not include any source_raw files, so the "
                        "capture cannot be materialized."
                    ),
                }
            )
            mark_missing_source_raw_capture_blocked(planned_items)
        return capture_blocked_plan(file_count=len(source_items))

    source_folder = distinct_sources[0] if distinct_sources else ""
    session_manifest_fingerprint = manifest_fingerprint(raw_items)
    workspace_root = path_from_ref(request.workspace_root_ref)
    capture_label = planned_capture_label(
        report_dir=report_dir,
        workspace_root=workspace_root,
        source_folder=source_folder,
        manifest_fingerprint_value=session_manifest_fingerprint,
    )
    for index, item in enumerate(planned_items):
        if item.category != "source_raw":
            continue
        planned_items[index] = replace(
            item,
            capture_label=capture_label,
            target_path=source_raw_target_path_for_item(
                item,
                workspace_root=workspace_root,
                source_folder=source_folder,
                capture_label=capture_label,
            ),
        )
    observed_period_start = min(
        (
            item.observed_period_start
            for item in raw_items
            if item.observed_period_start
        ),
        default="",
    )
    observed_period_end = max(
        (item.observed_period_end for item in raw_items if item.observed_period_end),
        default="",
    )
    observed_group_count = len(
        {item.observed_period_label for item in raw_items if item.observed_period_label}
    )
    duplicate_capture_uid = ""
    overlap_capture_uids: list[str] = []
    capture_status = "planned"
    for row in read_capture_rows(artifacts, path_from_ref(request.workspace_root_ref)):
        if row.get("source", "") != source_folder:
            continue
        if (
            row.get("manifest_fingerprint", "") == session_manifest_fingerprint
            and session_manifest_fingerprint
        ):
            duplicate_capture_uid = row.get("capture_uid", "")
            capture_status = "duplicate_blocked"
            break
        if overlaps(observed_period_start, observed_period_end, row):
            overlap_capture_uids.append(row.get("capture_uid", ""))
    if capture_status != "duplicate_blocked" and overlap_capture_uids:
        capture_status = "overlap_review_required"
    if capture_status == "duplicate_blocked":
        mark_non_materialized_capture_items(
            planned_items,
            capture_status=capture_status,
            placement_status="duplicate_capture_skip",
        )
    return CaptureSessionPlan(
        source_folder=source_folder,
        capture_label=capture_label,
        manifest_fingerprint=session_manifest_fingerprint,
        capture_status=capture_status,
        file_count=len(raw_items),
        observed_period_start=observed_period_start,
        observed_period_end=observed_period_end,
        observed_group_count=observed_group_count,
        duplicate_capture_uid=duplicate_capture_uid,
        overlap_capture_uids=tuple(uid for uid in overlap_capture_uids if uid),
    )


def apply_capture_session_plan(
    *,
    artifacts: ArtifactStorePort,
    report_dir: Path,
    plan: CaptureSessionPlan,
    context: CaptureSessionSummaryContext,
    summary_capture_status: str | None = None,
) -> None:
    summary = plan.to_summary(
        planned_items=context.planned_items, issue_rows=context.issue_rows
    )
    if summary_capture_status is not None:
        summary["capture_status"] = summary_capture_status
    summary["copied_count"] = context.copied_count
    artifacts.write_json(report_dir / "intake_summary.json", summary)
