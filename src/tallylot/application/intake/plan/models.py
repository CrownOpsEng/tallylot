"""Typed rows and headers for intake plan artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tallylot.application.intake.captures.session import CaptureSessionPlan

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
class PlannedItemBatch:
    planned_items: tuple[PlannedItem, ...]
    issue_rows: tuple[dict[str, str], ...]
    capture_session_plan: CaptureSessionPlan
