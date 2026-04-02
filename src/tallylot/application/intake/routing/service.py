"""Typed intake routing rules."""

from __future__ import annotations

from pathlib import Path

from tallylot.application.intake.archive import ScannedFile
from tallylot.application.intake.file_facts import IntakeFileFacts, detect_capture_id
from tallylot.ports.adapter_contracts import AdapterCapability
from tallylot.ports.intake_routing import IntakeRoutingRequest
from tallylot.ports.source_adapters import SourceAdapter, SourceAdapterRegistryPort

from .models import IntakeRoute
from .targets import RAW_SOURCE_SUFFIXES, is_working_derivative, raw_source_target_path, relative_target_path


def route_intake_file(
    entry: ScannedFile,
    *,
    registry: SourceAdapterRegistryPort,
    incoming_dir: Path,
    workspace_root: Path,
    facts: IntakeFileFacts,
) -> IntakeRoute:
    request = IntakeRoutingRequest(
        relative_path=entry.relative_path,
        file_path=entry.file_path,
        incoming_dir=incoming_dir,
        workspace_root=workspace_root,
        facts=facts,
        archive_source_path=entry.archive_source_path,
        archive_member_path=entry.archive_member_path,
    )
    route = _route_via_adapter(registry, request)
    if route is not None:
        return route

    route_key = request.route_key
    source_folder = _detect_source_folder(registry, route_key, facts)
    capture_id = detect_capture_id(route_key, facts) or incoming_dir.name
    relative_target = relative_target_path(route_key)
    if is_working_derivative(route_key):
        return IntakeRoute(
            category="supporting_artifact",
            role="working_derivative",
            source_folder=source_folder,
            capture_id=capture_id,
            action="extract_copy" if entry.archive_member_path else "copy",
            target_path=(
                workspace_root
                / "working"
                / "supporting_artifacts"
                / source_folder
                / incoming_dir.name
                / relative_target
            ),
        )
    if Path(route_key).suffix.lower() in RAW_SOURCE_SUFFIXES:
        target_path = raw_source_target_path(
            entry,
            workspace_root=workspace_root,
            source_folder=source_folder,
            capture_id=capture_id,
            relative_target=relative_target,
        )
        return IntakeRoute(
            category="source_raw",
            role="source_export",
            source_folder=source_folder,
            capture_id=capture_id,
            action="extract_copy" if entry.archive_member_path else "copy",
            target_path=target_path,
        )
    return IntakeRoute(
        category="supporting_artifact",
        role="supporting_artifact",
        source_folder=source_folder,
        capture_id=capture_id,
        action="extract_copy" if entry.archive_member_path else "copy",
        target_path=(
            workspace_root / "working" / "supporting_artifacts" / source_folder / incoming_dir.name / relative_target
        ),
    )


def _detect_source_folder(
    registry: SourceAdapterRegistryPort,
    relative_path: str,
    facts: IntakeFileFacts,
) -> str:
    matches = _matching_adapters(registry, relative_path, facts)
    if not matches:
        return "unclassified"
    return str(matches[0].manifest.adapter_id)


def _route_via_adapter(
    registry: SourceAdapterRegistryPort,
    request: IntakeRoutingRequest,
) -> IntakeRoute | None:
    for adapter in _matching_adapters(registry, request.route_key, request.facts):
        route = adapter.route_intake(request)
        if route is not None:
            return route
    return None


def _matching_adapters(
    registry: SourceAdapterRegistryPort,
    relative_path: str,
    facts: IntakeFileFacts,
) -> tuple[SourceAdapter, ...]:
    matches = [
        (adapter.match_intake(relative_path, facts), adapter)
        for adapter in registry.source_adapters
        if AdapterCapability.INTAKE_ROUTE in adapter.manifest.capabilities
    ]
    scored_matches = [(score, adapter) for score, adapter in matches if score > 0]
    scored_matches.sort(key=lambda item: (item[0], str(item[1].manifest.adapter_id)), reverse=True)
    return tuple(adapter for _, adapter in scored_matches)
