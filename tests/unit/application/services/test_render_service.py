from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from crypto_reconciliation.application.dtos import RenderCoinTrackingRequest
from crypto_reconciliation.application.services.render import CoinTrackingRenderService
from crypto_reconciliation.domain.models import AdapterCapability, AdapterManifest, CanonicalEvent
from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, EventId, SourceId
from crypto_reconciliation.infrastructure.serialization.csv_io import write_rows
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from crypto_reconciliation.ports.adapters import OutputAdapter, RenderedArtifact


@dataclass(frozen=True)
class FakeOutputRegistry:
    adapter: OutputAdapter

    @property
    def output_adapters(self) -> tuple[OutputAdapter, ...]:
        return (self.adapter,)

    def output_adapter(self, adapter_id: str) -> OutputAdapter:
        if str(self.adapter.manifest.adapter_id) != adapter_id:
            raise KeyError(adapter_id)
        return self.adapter


class FakeOutputAdapter:
    def __init__(self, *, supported: bool, capabilities: frozenset[AdapterCapability]) -> None:
        self.manifest = AdapterManifest(
            adapter_id=AdapterId("cointracking_csv"),
            display_name="CoinTracking CSV",
            version="1.0.0",
            capabilities=capabilities,
            supported=supported,
        )

    def render(self, events: tuple[CanonicalEvent, ...], output_path: Path) -> RenderedArtifact:
        del events, output_path
        raise AssertionError("render should not be called when adapter validation fails")


def test_render_service_rejects_unsupported_output_adapters(tmp_path: Path) -> None:
    canonical_events_path = _write_canonical_events(tmp_path)
    service = CoinTrackingRenderService(
        FakeOutputRegistry(
            FakeOutputAdapter(
                supported=False,
                capabilities=frozenset({AdapterCapability.OUTPUT_RENDER}),
            )
        ),
        FilesystemArtifactStore(),
    )

    with pytest.raises(ValueError, match="is not supported for rendering"):
        service.execute(
            RenderCoinTrackingRequest(
                canonical_events_path=canonical_events_path,
                output_path=tmp_path / "cointracking.csv",
            )
        )


def test_render_service_rejects_adapters_without_render_capability(tmp_path: Path) -> None:
    canonical_events_path = _write_canonical_events(tmp_path)
    service = CoinTrackingRenderService(
        FakeOutputRegistry(
            FakeOutputAdapter(
                supported=True,
                capabilities=frozenset(),
            )
        ),
        FilesystemArtifactStore(),
    )

    with pytest.raises(ValueError, match="does not declare render capability"):
        service.execute(
            RenderCoinTrackingRequest(
                canonical_events_path=canonical_events_path,
                output_path=tmp_path / "cointracking.csv",
            )
        )


def _write_canonical_events(tmp_path: Path) -> Path:
    path = tmp_path / "canonical_events.csv"
    row = CanonicalEvent(
        event_id=EventId("evt-1"),
        source=SourceId("fixture"),
        adapter_id=AdapterId("structured_csv"),
        account="Fixture",
        wallet="Primary",
        timestamp=datetime(2023, 8, 6, 10, 0, 0, tzinfo=UTC),
        event_kind="Trade",
        asset_in=AssetSymbol("BTC"),
        amount_in=Decimal("1"),
        asset_out=AssetSymbol("CAD"),
        amount_out=Decimal("10"),
        fee_asset=AssetSymbol("CAD"),
        fee_amount=Decimal("0.1"),
        tx_hash="tx-1",
    ).to_row()
    write_rows(path, tuple(row.keys()), (row,))
    return path
