"""Capture-session planning for intake runs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from typing import Protocol
from typing import TypeVar
from typing import cast

from tallylot.domain.captures import format_capture_label
from tallylot.domain.types import JsonValue
from tallylot.ports.artifacts import ArtifactStorePort

from ..contracts import IntakePlanRequest
from ..routing.targets import RawSidecarTarget, required_raw_sidecar_path
from ...resource_refs import path_from_ref


class _PlannedItem(Protocol):
    @property
    def action(self) -> str: ...

    @property
    def archive_member_path(self) -> str: ...

    @property
    def archive_source_path(self) -> str: ...

    @property
    def bundle_id(self) -> str: ...

    @property
    def bundle_relative_path(self) -> str: ...

    @property
    def capture_label(self) -> str: ...

    @property
    def category(self) -> str: ...

    @property
    def observed_period_end(self) -> str: ...

    @property
    def observed_period_label(self) -> str: ...

    @property
    def observed_period_start(self) -> str: ...

    @property
    def package_status(self) -> str: ...

    @property
    def placement_status(self) -> str: ...

    @property
    def relative_path(self) -> str: ...

    @property
    def review_codes(self) -> str: ...

    @property
    def review_reason(self) -> str: ...

    @property
    def role(self) -> str: ...

    @property
    def sha256(self) -> str: ...

    @property
    def source_folder(self) -> str: ...

    @property
    def source_resolution_status(self) -> str: ...


_PlannedItemT = TypeVar("_PlannedItemT", bound=_PlannedItem)


@dataclass(frozen=True)
class CaptureSessionPlan:
    source_folder: str
    capture_label: str
    manifest_fingerprint: str
    capture_status: str
    file_count: int
    observed_period_start: str
    observed_period_end: str
    observed_group_count: int
    duplicate_capture_uid: str = ""
    overlap_capture_uids: tuple[str, ...] = ()

    def to_summary(
        self,
        *,
        planned_items: Sequence[_PlannedItem],
        issue_rows: list[dict[str, str]],
    ) -> dict[str, JsonValue]:
        return {
            "source": self.source_folder,
            "planned_capture_label": self.capture_label,
            "manifest_fingerprint": self.manifest_fingerprint,
            "capture_status": self.capture_status,
            "observed_period_start": self.observed_period_start,
            "observed_period_end": self.observed_period_end,
            "observed_group_count": self.observed_group_count,
            "duplicate_capture_uid": self.duplicate_capture_uid,
            "overlap_capture_uids": list(self.overlap_capture_uids),
            "file_count": self.file_count,
            "issue_count": len(issue_rows),
            "planned_copy_count": sum(
                1 for item in planned_items if item.action in {"copy", "extract_copy"}
            ),
            "copied_count": 0,
            "explicit_map_count": sum(
                1
                for item in planned_items
                if item.source_resolution_status == "explicit_map"
            ),
            "explicit_map_blocked_count": sum(
                1
                for item in planned_items
                if item.source_resolution_status == "explicit_map_blocked"
            ),
            "source_label_map_issue_count": sum(
                1 for row in issue_rows if row["kind"].startswith("source_label_map_")
            ),
            "duplicate_packages": _package_count(planned_items, "duplicate_package"),
            "merge_primary_packages": _package_count(planned_items, "merge_primary"),
            "merged_packages": _package_count(planned_items, "merge_member"),
            "overlap_packages": _package_count(planned_items, "overlap_partial_review"),
            "mixed_cycle_packages": _package_count(planned_items, "mixed_cycle_review"),
        }


@dataclass(frozen=True)
class CaptureSessionSummaryContext:
    planned_items: Sequence[_PlannedItem]
    issue_rows: list[dict[str, str]]
    copied_count: int


def build_capture_session_plan(
    *,
    planned_items: list[_PlannedItemT],
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
        _mark_mixed_source_capture_blocked(planned_items)
        return _capture_blocked_plan(file_count=len(source_items))
    if not raw_items:
        if source_items:
            _mark_non_materialized_capture_items(
                planned_items,
                capture_status="capture_blocked",
                placement_status="capture_blocked_skip",
            )
            _mark_source_raw_items_capture_blocked(planned_items)
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
            _mark_missing_source_raw_capture_blocked(planned_items)
        return _capture_blocked_plan(file_count=len(source_items))

    source_folder = distinct_sources[0] if distinct_sources else ""
    manifest_fingerprint = _manifest_fingerprint(raw_items)
    workspace_root = path_from_ref(request.workspace_root_ref)
    capture_label = _planned_capture_label(
        report_dir=report_dir,
        workspace_root=workspace_root,
        source_folder=source_folder,
        manifest_fingerprint=manifest_fingerprint,
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
    for row in _read_capture_rows(artifacts, path_from_ref(request.workspace_root_ref)):
        if row.get("source", "") != source_folder:
            continue
        if (
            row.get("manifest_fingerprint", "") == manifest_fingerprint
            and manifest_fingerprint
        ):
            duplicate_capture_uid = row.get("capture_uid", "")
            capture_status = "duplicate_blocked"
            break
        if _overlaps(observed_period_start, observed_period_end, row):
            overlap_capture_uids.append(row.get("capture_uid", ""))
    if capture_status != "duplicate_blocked" and overlap_capture_uids:
        capture_status = "overlap_review_required"
    if capture_status == "duplicate_blocked":
        _mark_non_materialized_capture_items(
            planned_items,
            capture_status=capture_status,
            placement_status="duplicate_capture_skip",
        )
    for index, item in enumerate(planned_items):
        if item.category != "source_raw":
            continue
        target_path = _source_raw_target_path_for_item(
            item,
            workspace_root=path_from_ref(request.workspace_root_ref),
            source_folder=source_folder,
            capture_label=capture_label,
        )
        planned_items[index] = cast(
            _PlannedItemT,
            replace(
                cast(Any, item),
                capture_label=capture_label,
                capture_status=capture_status,
                target_path=target_path,
            ),
        )
    return CaptureSessionPlan(
        source_folder=source_folder,
        capture_label=capture_label,
        manifest_fingerprint=manifest_fingerprint,
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
    artifacts.write_json(report_dir / "intake_summary.json", cast(JsonValue, summary))


def _planned_capture_label(
    *,
    report_dir: Path,
    workspace_root: Path,
    source_folder: str,
    manifest_fingerprint: str,
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
        planned = payload.get("planned_capture_label", "")
        planned_manifest_fingerprint = payload.get("manifest_fingerprint", "")
        planned_source = payload.get("source", "")
        if (
            isinstance(planned, str)
            and planned.strip()
            and isinstance(planned_manifest_fingerprint, str)
            and planned_manifest_fingerprint == manifest_fingerprint
            and isinstance(planned_source, str)
            and planned_source == source_folder
            and not _capture_label_exists(
                workspace_root=workspace_root,
                source_folder=source_folder,
                capture_label=planned,
            )
        ):
            return planned
    return _next_capture_label(
        workspace_root=workspace_root, source_folder=source_folder
    )


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


def _capture_blocked_plan(
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


def _mark_source_raw_items_capture_blocked(
    planned_items: list[_PlannedItemT],
) -> None:
    for index, item in enumerate(planned_items):
        if item.category != "source_raw":
            continue
        planned_items[index] = cast(
            _PlannedItemT,
            replace(
                cast(Any, item),
                capture_label="",
                capture_status="capture_blocked",
            ),
        )


def _mark_non_materialized_capture_items(
    planned_items: list[_PlannedItemT],
    *,
    capture_status: str,
    placement_status: str,
) -> None:
    for index, item in enumerate(planned_items):
        replacement = cast(
            _PlannedItemT,
            replace(
                cast(Any, item),
                action=(
                    "skip" if item.action in {"copy", "extract_copy"} else item.action
                ),
                placement_status=(
                    placement_status
                    if item.action in {"copy", "extract_copy"}
                    else item.placement_status
                ),
                capture_status=capture_status,
            ),
        )
        planned_items[index] = replacement


def _mark_missing_source_raw_capture_blocked(
    planned_items: list[_PlannedItemT],
) -> None:
    _mark_non_materialized_capture_items(
        planned_items,
        capture_status="capture_blocked",
        placement_status="capture_blocked_skip",
    )
    for index, item in enumerate(planned_items):
        planned_items[index] = cast(
            _PlannedItemT,
            replace(
                cast(Any, item),
                review_required="yes",
                review_codes=_merge_value(
                    item.review_codes, "missing_source_raw_capture"
                ),
                review_reason=_merge_value(
                    item.review_reason,
                    "Intake run did not include any source_raw files.",
                ),
            ),
        )


def _mark_mixed_source_capture_blocked(planned_items: list[_PlannedItemT]) -> None:
    _mark_non_materialized_capture_items(
        planned_items,
        capture_status="capture_blocked",
        placement_status="mixed_source_capture_blocked",
    )
    for index, item in enumerate(planned_items):
        planned_items[index] = cast(
            _PlannedItemT,
            replace(
                cast(Any, item),
                review_required="yes",
                review_codes=_merge_value(item.review_codes, "mixed_source_capture"),
                review_reason=_merge_value(
                    item.review_reason,
                    "Intake run resolved multiple source folders.",
                ),
                capture_status="capture_blocked",
            ),
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


def _manifest_fingerprint(items: Sequence[_PlannedItem]) -> str:
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


def _read_capture_rows(
    artifacts: ArtifactStorePort, workspace_root: Path
) -> list[dict[str, str]]:
    path = workspace_root / "analysis" / "inventory" / "source_captures.csv"
    if not path.exists():
        return []
    return artifacts.read_rows(path)


def _overlaps(start: str, end: str, row: dict[str, str]) -> bool:
    existing_start = row.get("observed_period_start", "")
    existing_end = row.get("observed_period_end", "")
    if not start or not end or not existing_start or not existing_end:
        return False
    return not (end < existing_start or existing_end < start)


def _source_raw_target_path_for_item(
    item: _PlannedItem,
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


def _package_count(planned_items: Sequence[_PlannedItem], package_status: str) -> int:
    return len(
        {
            (item.source_folder, item.capture_label, item.bundle_id)
            for item in planned_items
            if item.package_status == package_status
            or (
                package_status == "duplicate_package"
                and item.package_status.startswith("duplicate_package")
            )
        }
    )
