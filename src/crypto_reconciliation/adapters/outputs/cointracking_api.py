"""Stub CoinTracking API output adapter entry point."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.domain.models import AdapterCapability, AdapterManifest, CanonicalEvent
from crypto_reconciliation.domain.types import AdapterId
from crypto_reconciliation.ports.adapters import RenderedArtifact


class CoinTrackingApiStubAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("cointracking_api"),
        display_name="CoinTracking API",
        version="0.0.0",
        capabilities=frozenset({AdapterCapability.OUTPUT_RENDER}),
        supported=False,
        description="Reserved API adapter entry point.",
    )

    def render(self, events: tuple[CanonicalEvent, ...], output_path: Path) -> RenderedArtifact:
        del events, output_path
        raise NotImplementedError(
            "CoinTracking API integration is intentionally stubbed in this phase.",
        )


ADAPTER = CoinTrackingApiStubAdapter()
