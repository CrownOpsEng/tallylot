"""Per-entry intake planning helpers."""

from __future__ import annotations

from tallylot.application.intake.contracts import IntakePlanRequest
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.source_adapters import SourceAdapterRegistryPort

from ..archive import ScannedFile
from ..file_facts import inspect_intake_file
from ..inventory import resolve_inventory_route
from ..overlap import IntakeOverlapRequest, resolve_overlap_review
from ..path_rules import (
    bundle_id,
    bundle_relative_path,
    override_target_source,
    package_key,
    source_raw_target_path,
)
from ..routing import route_intake_file
from .models import PlannedItem
from .reviews import merge_review_required, merge_review_values


def build_planned_item(
    entry: ScannedFile,
    *,
    registry: SourceAdapterRegistryPort,
    artifacts: ArtifactStorePort,
    request: IntakePlanRequest,
) -> PlannedItem:
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
    return PlannedItem(
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
