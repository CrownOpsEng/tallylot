"""Explicit output projection service."""

from __future__ import annotations

from crypto_reconciliation.application.models.output import (
    RenderOutputRequest,
    RenderOutputResponse,
)
from crypto_reconciliation.application.services.parsers import load_canonical_events
from crypto_reconciliation.domain.models import AdapterCapability
from crypto_reconciliation.ports.adapters import OutputAdapterRegistryPort
from crypto_reconciliation.ports.artifacts import ArtifactStorePort


class OutputProjectionService:
    def __init__(self, registry: OutputAdapterRegistryPort, artifacts: ArtifactStorePort) -> None:
        self._registry = registry
        self._artifacts = artifacts

    def execute(self, request: RenderOutputRequest) -> RenderOutputResponse:
        events = load_canonical_events(request.canonical_events_path, self._artifacts)
        adapter = self._registry.output_adapter(request.output_adapter)
        if not adapter.manifest.supported:
            raise ValueError(f"output adapter {adapter.manifest.adapter_id} is not supported for rendering")
        if AdapterCapability.OUTPUT_RENDER not in adapter.manifest.capabilities:
            raise ValueError(f"output adapter {adapter.manifest.adapter_id} does not declare render capability")
        artifact = adapter.render(events, request.output_path)
        return RenderOutputResponse(output_path=artifact.path, row_count=artifact.row_count)
