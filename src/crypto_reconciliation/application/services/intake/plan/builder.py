"""Plan-row assembly for intake workflows."""

from __future__ import annotations

from crypto_reconciliation.application.models.source import IntakePlanRequest
from crypto_reconciliation.ports.adapters import SourceAdapterRegistryPort
from crypto_reconciliation.ports.artifacts import ArtifactStorePort

from ..archive import ScannedFile
from .entry import build_planned_item
from .finalize import apply_package_rules_to_items
from .models import PlannedItem


def build_planned_items(
    files: tuple[ScannedFile, ...],
    registry: SourceAdapterRegistryPort,
    artifacts: ArtifactStorePort,
    request: IntakePlanRequest,
) -> list[PlannedItem]:
    planned_items = [
        build_planned_item(entry, registry=registry, artifacts=artifacts, request=request) for entry in files
    ]
    return apply_package_rules_to_items(planned_items, request=request)
