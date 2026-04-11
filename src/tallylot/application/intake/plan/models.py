"""Typed rows, headers, and capture-session models for intake plan artifacts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from tallylot.domain.types import JsonValue

PLAN_HEADER = (
    "path",
    "relative_path",
    "archive_source_path",
    "archive_member_path",
    "category",
    "role",
    "evidence_role",
    "originality_class",
    "source_folder",
    "capture_label",
    "capture_status",
    "bundle_id",
    "bundle_relative_path",
    "observed_period_start",
    "observed_period_end",
    "observed_period_label",
    "action",
    "package_key",
    "package_status",
    "package_primary_bundle_id",
    "package_related_bundles",
    "package_cycle_status",
    "package_scope_status",
    "package_decision_reason",
    "package_row_status",
    "placement_status",
    "source_resolution_status",
    "source_resolution_reason",
    "review_required",
    "review_codes",
    "review_reason",
    "inventory_match_status",
    "target_path",
)


@dataclass(frozen=True)
class PlannedItem:
    source_path: Path
    relative_path: str
    archive_source_path: str
    archive_member_path: str
    category: str
    role: str
    evidence_role: str
    originality_class: str
    source_folder: str
    capture_label: str
    capture_status: str
    bundle_id: str
    bundle_relative_path: str
    observed_period_start: str
    observed_period_end: str
    observed_period_label: str
    action: str
    package_key: str
    package_status: str
    package_primary_bundle_id: str
    package_related_bundles: str
    package_cycle_status: str
    package_scope_status: str
    package_decision_reason: str
    package_row_status: str
    placement_status: str
    source_resolution_status: str
    source_resolution_reason: str
    review_required: str
    review_codes: str
    review_reason: str
    inventory_match_status: str
    sha256: str
    scope_tokens: tuple[str, ...]
    target_path: Path

    def to_row(self) -> dict[str, str]:
        return {
            "path": str(self.source_path),
            "relative_path": self.relative_path,
            "archive_source_path": self.archive_source_path,
            "archive_member_path": self.archive_member_path,
            "category": self.category,
            "role": self.role,
            "evidence_role": self.evidence_role,
            "originality_class": self.originality_class,
            "source_folder": self.source_folder,
            "capture_label": self.capture_label,
            "capture_status": self.capture_status,
            "bundle_id": self.bundle_id,
            "bundle_relative_path": self.bundle_relative_path,
            "observed_period_start": self.observed_period_start,
            "observed_period_end": self.observed_period_end,
            "observed_period_label": self.observed_period_label,
            "action": self.action,
            "package_key": self.package_key,
            "package_status": self.package_status,
            "package_primary_bundle_id": self.package_primary_bundle_id,
            "package_related_bundles": self.package_related_bundles,
            "package_cycle_status": self.package_cycle_status,
            "package_scope_status": self.package_scope_status,
            "package_decision_reason": self.package_decision_reason,
            "package_row_status": self.package_row_status,
            "placement_status": self.placement_status,
            "source_resolution_status": self.source_resolution_status,
            "source_resolution_reason": self.source_resolution_reason,
            "review_required": self.review_required,
            "review_codes": self.review_codes,
            "review_reason": self.review_reason,
            "inventory_match_status": self.inventory_match_status,
            "target_path": str(self.target_path),
        }


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
        planned_items: Sequence[PlannedItem],
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
    planned_items: Sequence[PlannedItem]
    issue_rows: list[dict[str, str]]
    copied_count: int


def _package_count(planned_items: Sequence[PlannedItem], package_status: str) -> int:
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


@dataclass(frozen=True)
class PlannedItemBatch:
    planned_items: tuple[PlannedItem, ...]
    issue_rows: tuple[dict[str, str], ...]
    capture_session_plan: CaptureSessionPlan
