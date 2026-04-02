"""CoinTracking render service."""

from __future__ import annotations

from crypto_reconciliation.application.dtos import (
    RenderCoinTrackingRequest,
    RenderCoinTrackingResponse,
)
from crypto_reconciliation.application.services.parsers import load_canonical_events
from crypto_reconciliation.infrastructure.discovery.adapters import AdapterRegistry


class CoinTrackingRenderService:
    def __init__(self, registry: AdapterRegistry) -> None:
        self._registry = registry

    def execute(self, request: RenderCoinTrackingRequest) -> RenderCoinTrackingResponse:
        events = load_canonical_events(request.canonical_events_path)
        adapter = self._registry.output_adapter("cointracking_csv")
        artifact = adapter.render(events, request.output_path)
        return RenderCoinTrackingResponse(output_path=artifact.path, row_count=artifact.row_count)
