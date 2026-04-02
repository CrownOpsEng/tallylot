"""Stub CoinTracking API output adapter entry point."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.domain.transactions import TransactionFact
from crypto_reconciliation.domain.types import AdapterId
from crypto_reconciliation.ports.adapter_contracts import AdapterCapability, AdapterManifest
from crypto_reconciliation.ports.output_adapters import RenderedArtifact


class CoinTrackingApiStubAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("cointracking_api"),
        display_name="CoinTracking API",
        version="0.0.0",
        capabilities=frozenset({AdapterCapability.OUTPUT_RENDER}),
        supported=False,
        description="Reserved API adapter entry point.",
    )

    def render(self, facts: tuple[TransactionFact, ...], output_path: Path) -> RenderedArtifact:
        del facts, output_path
        raise NotImplementedError(
            "CoinTracking API integration is intentionally stubbed in this phase.",
        )


ADAPTER = CoinTrackingApiStubAdapter()
