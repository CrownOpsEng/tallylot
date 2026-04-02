"""CoinTracking CSV output adapter."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.domain.transactions import TransactionFact
from crypto_reconciliation.domain.types import AdapterId
from crypto_reconciliation.ports.adapter_contracts import AdapterCapability, AdapterManifest
from crypto_reconciliation.ports.output_adapters import RenderedArtifact

from .rendering import render as render_output


class CoinTrackingCsvAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("cointracking_csv"),
        display_name="CoinTracking CSV",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.OUTPUT_RENDER}),
        description="Render transaction facts into CoinTracking-compatible CSV rows.",
    )

    def render(self, facts: tuple[TransactionFact, ...], output_path: Path) -> RenderedArtifact:
        return render_output(facts, output_path)


ADAPTER = CoinTrackingCsvAdapter()
