"""Plan-row assembly for intake workflows."""

from __future__ import annotations

from crypto_reconciliation.application.models.source import IntakePlanRequest
from crypto_reconciliation.ports.adapters import SourceAdapterRegistryPort
from crypto_reconciliation.ports.artifacts import ArtifactStorePort

from .archive import ScannedFile
from .file_facts import inspect_intake_file
from .inventory import resolve_inventory_route
from .overlap import IntakeOverlapRequest, resolve_overlap_review
from .packages import PlannedPackageItem, apply_package_rules
from .path_rules import (
    bundle_id,
    bundle_relative_path,
    effective_bundle_id,
    override_target_source,
    package_key,
    source_raw_target_path,
)
from .plan_models import PlannedItem
from .reviews import (
    merge_review_required,
    merge_review_values,
    planned_review_codes,
    planned_review_reason,
    planned_review_required,
)
from .routing import route_intake_file


def build_planned_items(
    files: tuple[ScannedFile, ...],
    registry: SourceAdapterRegistryPort,
    artifacts: ArtifactStorePort,
    request: IntakePlanRequest,
) -> list[PlannedItem]:
    planned_items: list[PlannedItem] = []
    for entry in files:
        relative_path = entry.archive_member_path or entry.relative_path
        facts = inspect_intake_file(entry.file_path, relative_path=relative_path)
        route = route_intake_file(
            entry,
            registry=registry,
            incoming_dir=request.incoming_dir,
            workspace_root=request.workspace_root,
            facts=facts,
        )
        bundle_id_value = bundle_id(entry, source_folder=route.source_folder)
        bundle_relative_path_value = bundle_relative_path(entry)
        inventory_route = resolve_inventory_route(
            artifacts=artifacts,
            workspace_root=request.workspace_root,
            source_folder=route.source_folder,
            facts=facts,
        )
        overlap_review = resolve_overlap_review(
            artifacts=artifacts,
            request=IntakeOverlapRequest(
                workspace_root=request.workspace_root,
                source_folder=inventory_route.source_folder,
                capture_id=route.capture_id,
                relative_path=relative_path,
                sha256=entry.sha256,
                size_bytes=entry.size_bytes,
                facts=facts,
            ),
        )
        source_target_path = (
            source_raw_target_path(
                request.workspace_root,
                source_folder=inventory_route.source_folder,
                capture_id=route.capture_id,
                bundle_id_value=bundle_id_value,
                bundle_relative_path_value=bundle_relative_path_value,
            )
            if route.category == "source_raw"
            else override_target_source(route.target_path, route.source_folder, inventory_route.source_folder)
        )
        planned_items.append(
            PlannedItem(
                source_path=entry.file_path,
                relative_path=relative_path,
                archive_source_path=entry.archive_source_path,
                archive_member_path=entry.archive_member_path,
                category=route.category,
                role=route.role,
                source_folder=inventory_route.source_folder,
                capture_id=route.capture_id,
                bundle_id=bundle_id_value,
                bundle_relative_path=bundle_relative_path_value,
                action=route.action,
                package_key=package_key(entry),
                package_status="primary",
                package_primary_bundle_id=bundle_id_value,
                package_related_bundles="",
                package_cycle_status="",
                package_scope_status="",
                package_decision_reason="",
                package_row_status="package_keep",
                placement_status="planned_copy" if route.action in {"copy", "extract_copy"} else "inspect_only",
                review_required=merge_review_required(
                    route.review_required,
                    inventory_route.review_required,
                    overlap_review.review_required,
                ),
                review_codes=merge_review_values(
                    route.review_codes,
                    inventory_route.review_codes,
                    overlap_review.review_codes,
                ),
                review_reason=merge_review_values(
                    route.review_reason,
                    inventory_route.review_reason,
                    overlap_review.review_reason,
                ),
                inventory_match_status=inventory_route.inventory_match_status,
                sha256=entry.sha256,
                scope_tokens=facts.scope_tokens,
                target_path=source_target_path,
            )
        )
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
