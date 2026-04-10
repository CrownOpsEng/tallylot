"""Per-entry intake planning helpers."""

from __future__ import annotations

from tallylot.application.intake.contracts import IntakePlanRequest
from tallylot.application.intake.source_labels import (
    SourceLabelContext,
    SourceLabelResolutionRequest,
    resolve_source_label,
)
from tallylot.application.resource_refs import path_from_ref
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.source_adapters import SourceAdapterRegistryPort

from ..archive import ScannedFile
from ..file_facts import inspect_intake_file
from ..overlap import IntakeOverlapRequest, resolve_overlap_review
from ..path_rules import (
    bundle_id,
    bundle_relative_path,
    override_target_source,
    package_key,
    source_raw_target_path,
)
from ..routing import route_intake_file
from ..routing.targets import WORKING_DERIVATIVE_SUFFIXES
from .models import PlannedItem
from .reviews import merge_review_required, merge_review_values


def build_planned_item(
    entry: ScannedFile,
    *,
    registry: SourceAdapterRegistryPort,
    artifacts: ArtifactStorePort,
    request: IntakePlanRequest,
    source_label_context: SourceLabelContext,
) -> PlannedItem:
    incoming_dir = path_from_ref(request.incoming_capture_ref)
    workspace_root = path_from_ref(request.workspace_root_ref)
    relative_path = entry.archive_member_path or entry.relative_path
    facts = inspect_intake_file(entry.file_path, relative_path=relative_path)
    route = route_intake_file(
        entry,
        registry=registry,
        incoming_dir=incoming_dir,
        workspace_root=workspace_root,
        facts=facts,
    )
    planned_capture_label = route.capture_label
    route_key = (
        entry.relative_path
        if not entry.archive_member_path
        else f"{entry.archive_source_path}::{entry.archive_member_path}"
    )
    source_resolution = resolve_source_label(
        artifacts=artifacts,
        context=source_label_context,
        request=SourceLabelResolutionRequest(
            workspace_root=workspace_root,
            route_key=route_key,
            facts=facts,
            source_folder=route.source_folder,
            target_path=route.target_path,
        ),
    )
    bundle_id_value = bundle_id(entry, source_folder=source_resolution.source_folder)
    bundle_relative_path_value = bundle_relative_path(entry)
    overlap_review = resolve_overlap_review(
        artifacts=artifacts,
        request=IntakeOverlapRequest(
            workspace_root=workspace_root,
            source_folder=source_resolution.source_folder,
            relative_path=relative_path,
            sha256=entry.sha256,
            size_bytes=entry.size_bytes,
            facts=facts,
        ),
    )
    source_target_path = (
        source_raw_target_path(
            workspace_root,
            source_folder=source_resolution.source_folder,
            capture_label=planned_capture_label,
            bundle_id_value=bundle_id_value,
            bundle_relative_path_value=bundle_relative_path_value,
        )
        if route.category == "source_raw"
        else override_target_source(
            route.target_path, route.source_folder, source_resolution.source_folder
        )
    )
    return PlannedItem(
        source_path=entry.file_path,
        relative_path=relative_path,
        archive_source_path=entry.archive_source_path,
        archive_member_path=entry.archive_member_path,
        category=route.category,
        role=route.role,
        evidence_role=_evidence_role(entry, route.category, route.role),
        originality_class=_originality_class(entry, route.category, route.role),
        source_folder=source_resolution.source_folder,
        capture_label=planned_capture_label,
        capture_status="planned",
        bundle_id=bundle_id_value,
        bundle_relative_path=bundle_relative_path_value,
        observed_period_start=facts.observed_period_start,
        observed_period_end=facts.observed_period_end,
        observed_period_label=facts.observed_period_label,
        action="skip" if source_resolution.blocked else route.action,
        package_key=package_key(entry),
        package_status="primary",
        package_primary_bundle_id=bundle_id_value,
        package_related_bundles="",
        package_cycle_status="",
        package_scope_status="",
        package_decision_reason="",
        package_row_status="package_keep",
        placement_status=(
            "mapping_blocked_skip"
            if source_resolution.blocked
            else "planned_copy"
            if route.action in {"copy", "extract_copy"}
            else "inspect_only"
        ),
        source_resolution_status=source_resolution.source_resolution_status,
        source_resolution_reason=source_resolution.source_resolution_reason,
        review_required=merge_review_required(
            route.review_required,
            source_resolution.review_required,
            overlap_review.review_required,
        ),
        review_codes=merge_review_values(
            route.review_codes,
            source_resolution.review_codes,
            overlap_review.review_codes,
        ),
        review_reason=merge_review_values(
            route.review_reason,
            source_resolution.review_reason,
            overlap_review.review_reason,
        ),
        inventory_match_status=source_resolution.inventory_match_status,
        sha256=entry.sha256,
        scope_tokens=facts.scope_tokens,
        target_path=source_target_path,
    )


def _evidence_role(entry: ScannedFile, category: str, role: str) -> str:
    suffix = entry.file_path.suffix.lower()
    if category != "source_raw":
        return "supporting_artifact"
    if role == "portfolio_export":
        return "portfolio_export"
    if role in {"portfolio_sidecar", "required_sidecar"}:
        return "required_sidecar"
    if suffix == ".pdf":
        return "statement_source"
    return "transaction_source"


def _originality_class(entry: ScannedFile, category: str, role: str) -> str:
    suffix = entry.file_path.suffix.lower()
    if category == "source_raw":
        return "upstream_original"
    if suffix in WORKING_DERIVATIVE_SUFFIXES:
        if suffix in {".xlsx", ".xls"}:
            return "operator_authored"
        return "derived_runtime"
    return "upstream_original"
