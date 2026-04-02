"""Package-rule application for planned intake rows."""

from __future__ import annotations

from crypto_reconciliation.application.models.source import IntakePlanRequest

from ..packages import PlannedPackageItem, apply_package_rules
from ..path_rules import effective_bundle_id, source_raw_target_path
from .models import PlannedItem
from .reviews import planned_review_codes, planned_review_reason, planned_review_required


def apply_package_rules_to_items(
    planned_items: list[PlannedItem],
    *,
    request: IntakePlanRequest,
) -> list[PlannedItem]:
    package_items = [
        PlannedPackageItem(
            path=str(item.source_path),
            relative_path=item.relative_path,
            archive_source_path=item.archive_source_path,
            source_folder=item.source_folder,
            capture_id=item.capture_id,
            category=item.category,
            action=item.action,
            sha256=item.sha256,
            bundle_id=item.bundle_id,
            bundle_relative_path=item.bundle_relative_path,
            scope_tokens=item.scope_tokens,
            package_status=item.package_status,
            package_primary_bundle_id=item.package_primary_bundle_id,
            package_related_bundles=item.package_related_bundles,
            package_cycle_status=item.package_cycle_status,
            package_scope_status=item.package_scope_status,
            package_decision_reason=item.package_decision_reason,
            package_row_status=item.package_row_status,
            placement_status=item.placement_status,
        )
        for item in planned_items
    ]
    updated_package_items, _ = apply_package_rules(package_items)
    package_map = {item.path: item for item in updated_package_items}
    return [
        PlannedItem(
            source_path=item.source_path,
            relative_path=item.relative_path,
            archive_source_path=item.archive_source_path,
            archive_member_path=item.archive_member_path,
            category=item.category,
            role=item.role,
            source_folder=item.source_folder,
            capture_id=item.capture_id,
            bundle_id=effective_bundle_id(item, package_map[str(item.source_path)]),
            bundle_relative_path=item.bundle_relative_path,
            action=package_map[str(item.source_path)].action,
            package_key=item.package_key,
            package_status=package_map[str(item.source_path)].package_status,
            package_primary_bundle_id=package_map[str(item.source_path)].package_primary_bundle_id,
            package_related_bundles=package_map[str(item.source_path)].package_related_bundles,
            package_cycle_status=package_map[str(item.source_path)].package_cycle_status,
            package_scope_status=package_map[str(item.source_path)].package_scope_status,
            package_decision_reason=package_map[str(item.source_path)].package_decision_reason,
            package_row_status=package_map[str(item.source_path)].package_row_status,
            placement_status=package_map[str(item.source_path)].placement_status,
            review_required=planned_review_required(item, package_map[str(item.source_path)]),
            review_codes=planned_review_codes(item, package_map[str(item.source_path)]),
            review_reason=planned_review_reason(item, package_map[str(item.source_path)]),
            inventory_match_status=item.inventory_match_status,
            sha256=item.sha256,
            scope_tokens=item.scope_tokens,
            target_path=(
                source_raw_target_path(
                    request.workspace_root,
                    source_folder=item.source_folder,
                    capture_id=item.capture_id,
                    bundle_id_value=effective_bundle_id(item, package_map[str(item.source_path)]),
                    bundle_relative_path_value=item.bundle_relative_path,
                )
                if item.category == "source_raw"
                else item.target_path
            ),
        )
        for item in planned_items
    ]
