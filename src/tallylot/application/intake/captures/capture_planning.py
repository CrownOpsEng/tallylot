"""Capture-session planning helpers for intake runs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from tallylot.application.intake.plan.models import CaptureSessionPlan, PlannedItem
from tallylot.domain.captures import format_capture_label
from tallylot.domain.types import JsonValue
from tallylot.ports.artifacts import ArtifactStorePort

from ..routing.targets import RawSidecarTarget, required_raw_sidecar_path


def planned_capture_label(
    *,
    report_dir: Path,
    workspace_root: Path,
    source_folder: str,
    manifest_fingerprint_value: str,
) -> str:
    summary_path = report_dir / "intake_summary.json"
    if summary_path.exists():
        try:
            payload_obj: object = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload_obj = {}
        payload = (
            cast(dict[str, JsonValue], payload_obj)
            if isinstance(payload_obj, dict)
            else {}
        )
        reusable_label = _reusable_planned_capture_label(
            payload=payload,
            workspace_root=workspace_root,
            source_folder=source_folder,
            manifest_fingerprint_value=manifest_fingerprint_value,
        )
        if reusable_label is not None:
            return reusable_label
    return _next_capture_label(
        workspace_root=workspace_root, source_folder=source_folder
    )


def _reusable_planned_capture_label(
    *,
    payload: dict[str, JsonValue],
    workspace_root: Path,
    source_folder: str,
    manifest_fingerprint_value: str,
) -> str | None:
    planned = payload.get("planned_capture_label", "")
    if not isinstance(planned, str) or not planned.strip():
        return None
    planned_manifest_fingerprint = payload.get("manifest_fingerprint", "")
    planned_source = payload.get("source", "")
    if planned_manifest_fingerprint != manifest_fingerprint_value:
        return None
    if planned_source != source_folder:
        return None
    if _capture_label_exists(
        workspace_root=workspace_root,
        source_folder=source_folder,
        capture_label=planned,
    ):
        return None
    return planned


def _capture_label_exists(
    *,
    workspace_root: Path,
    source_folder: str,
    capture_label: str,
) -> bool:
    if not source_folder or not capture_label:
        return False
    return (
        workspace_root / "evidence" / "raw" / "source" / source_folder / capture_label
    ).exists()


def mark_source_raw_items_capture_blocked(
    planned_items: list[PlannedItem],
) -> None:
    for index, item in enumerate(planned_items):
        if item.category != "source_raw":
            continue
        planned_items[index] = replace(
            item,
            capture_label="",
            capture_status="capture_blocked",
        )


def mark_non_materialized_capture_items(
    planned_items: list[PlannedItem],
    *,
    capture_status: str,
    placement_status: str,
) -> None:
    for index, item in enumerate(planned_items):
        replacement = replace(
            item,
            action="skip" if item.action in {"copy", "extract_copy"} else item.action,
            placement_status=(
                placement_status
                if item.action in {"copy", "extract_copy"}
                else item.placement_status
            ),
            capture_status=capture_status,
        )
        planned_items[index] = replacement


def mark_missing_source_raw_capture_blocked(
    planned_items: list[PlannedItem],
) -> None:
    for index, item in enumerate(planned_items):
        keep_support_copy = item.category != "source_raw" and item.action in {
            "copy",
            "extract_copy",
        }
        should_skip = (
            item.category == "source_raw" and item.action in {"copy", "extract_copy"}
        ) or (not keep_support_copy and item.action in {"copy", "extract_copy"})
        planned_items[index] = replace(
            item,
            action="skip" if should_skip else item.action,
            placement_status=(
                "capture_blocked_skip" if should_skip else item.placement_status
            ),
            capture_status="capture_blocked",
            review_required="yes",
            review_codes=_merge_value(item.review_codes, "missing_source_raw_capture"),
            review_reason=_merge_value(
                item.review_reason,
                "Intake run did not include any source_raw files.",
            ),
        )


def mark_mixed_source_capture_blocked(planned_items: list[PlannedItem]) -> None:
    for index, item in enumerate(planned_items):
        is_source_raw_copy = item.category == "source_raw" and item.action in {
            "copy",
            "extract_copy",
        }
        planned_items[index] = replace(
            item,
            action="skip" if is_source_raw_copy else item.action,
            placement_status=(
                "mixed_source_capture_blocked"
                if is_source_raw_copy
                else item.placement_status
            ),
            capture_label="" if item.category == "source_raw" else item.capture_label,
            capture_status="capture_blocked",
            review_required="yes",
            review_codes=_merge_value(item.review_codes, "mixed_source_capture"),
            review_reason=_merge_value(
                item.review_reason,
                "Intake run resolved multiple source folders.",
            ),
        )


def capture_blocked_plan(
    *, source_folder: str = "", file_count: int = 0
) -> CaptureSessionPlan:
    return CaptureSessionPlan(
        source_folder=source_folder,
        capture_label="",
        manifest_fingerprint="",
        capture_status="capture_blocked",
        file_count=file_count,
        observed_period_start="",
        observed_period_end="",
        observed_group_count=0,
    )


def _next_capture_label(*, workspace_root: Path, source_folder: str) -> str:
    label = format_capture_label(datetime.now(UTC))
    if not source_folder:
        return label
    source_root = workspace_root / "evidence" / "raw" / "source" / source_folder
    if not source_root.exists() or not (source_root / label).exists():
        return label
    suffix = 1
    while (source_root / f"{label}--{suffix:02d}").exists():
        suffix += 1
    return f"{label}--{suffix:02d}"


def manifest_fingerprint(items: Sequence[PlannedItem]) -> str:
    payload = json.dumps(
        [
            {
                "archive_member_path": item.archive_member_path,
                "archive_source_path": item.archive_source_path,
                "relative_path": item.relative_path,
                "sha256": item.sha256,
            }
            for item in sorted(
                items,
                key=lambda candidate: (
                    candidate.relative_path,
                    candidate.archive_member_path,
                ),
            )
        ],
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_capture_rows(
    artifacts: ArtifactStorePort, workspace_root: Path
) -> list[dict[str, str]]:
    path = workspace_root / "analysis" / "inventory" / "source_captures.csv"
    if not path.exists():
        return []
    return artifacts.read_rows(path)


def overlaps(start: str, end: str, row: dict[str, str]) -> bool:
    existing_start = row.get("observed_period_start", "")
    existing_end = row.get("observed_period_end", "")
    if not start or not end or not existing_start or not existing_end:
        return False
    return not (end < existing_start or existing_end < start)


def source_raw_target_path_for_item(
    item: PlannedItem,
    *,
    workspace_root: Path,
    source_folder: str,
    capture_label: str,
) -> Path:
    if item.role == "required_sidecar":
        return required_raw_sidecar_path(
            workspace_root,
            RawSidecarTarget(
                source_folder=source_folder,
                capture_label=capture_label,
                relative_path=item.relative_path,
                archive_source_path=item.archive_source_path,
                archive_member_path=item.archive_member_path,
            ),
        )
    capture_root = (
        workspace_root / "evidence" / "raw" / "source" / source_folder / capture_label
    )
    if item.bundle_id.endswith("-loose"):
        return capture_root / item.bundle_relative_path
    return capture_root / item.bundle_id / item.bundle_relative_path


def _merge_value(left: str, right: str) -> str:
    values = [value for value in (left, right) if value]
    return ";".join(values)
