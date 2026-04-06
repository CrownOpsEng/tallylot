"""Plan-row assembly for intake workflows."""

from __future__ import annotations

from tallylot.application.intake.contracts import IntakePlanRequest
from tallylot.application.intake.source_labels import load_source_label_context
from tallylot.application.resource_refs import path_from_ref
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.source_adapters import SourceAdapterRegistryPort

from ..archive import ScannedFile
from .entry import build_planned_item
from .finalize import apply_package_rules_to_items
from .models import PlannedItemBatch


def build_planned_items(
    files: tuple[ScannedFile, ...],
    registry: SourceAdapterRegistryPort,
    artifacts: ArtifactStorePort,
    request: IntakePlanRequest,
) -> PlannedItemBatch:
    source_label_context = load_source_label_context(
        artifacts, path_from_ref(request.workspace_root_ref)
    )
    planned_items = [
        build_planned_item(
            entry,
            registry=registry,
            artifacts=artifacts,
            request=request,
            source_label_context=source_label_context,
        )
        for entry in files
    ]
    return PlannedItemBatch(
        planned_items=tuple(
            apply_package_rules_to_items(planned_items, request=request)
        ),
        issue_rows=tuple(issue.to_row() for issue in source_label_context.issues),
    )
