from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from crypto_reconciliation.application.outputs import RenderOutputRequest, RenderOutputUseCase
from crypto_reconciliation.domain.transactions import (
    EconomicKind,
    EconomicLeg,
    FactClassification,
    JournalIntent,
    ProjectionType,
    TaxTreatmentCode,
    TransactionFact,
)
from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId
from crypto_reconciliation.infrastructure.storage import FilesystemFactRepository
from crypto_reconciliation.ports.adapter_contracts import AdapterCapability, AdapterManifest
from crypto_reconciliation.ports.output_adapters import OutputAdapter, RenderedArtifact


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

    def render(self, facts: tuple[TransactionFact, ...], output_path: Path) -> RenderedArtifact:
        del facts, output_path
        raise AssertionError("render should not be called when adapter validation fails")


def test_output_projection_service_rejects_unsupported_output_adapters(tmp_path: Path) -> None:
    facts_path = _write_facts(tmp_path)
    service = RenderOutputUseCase(
        FakeOutputRegistry(
            FakeOutputAdapter(
                supported=False,
                capabilities=frozenset({AdapterCapability.OUTPUT_RENDER}),
            )
        ),
        FilesystemFactRepository(),
    )

    with pytest.raises(ValueError, match="is not supported for rendering"):
        service.execute(
            RenderOutputRequest(
                output_adapter="cointracking_csv",
                facts_path=facts_path,
                output_path=tmp_path / "cointracking.csv",
            )
        )


def test_output_projection_service_rejects_adapters_without_render_capability(tmp_path: Path) -> None:
    facts_path = _write_facts(tmp_path)
    service = RenderOutputUseCase(
        FakeOutputRegistry(
            FakeOutputAdapter(
                supported=True,
                capabilities=frozenset(),
            )
        ),
        FilesystemFactRepository(),
    )

    with pytest.raises(ValueError, match="does not declare render capability"):
        service.execute(
            RenderOutputRequest(
                output_adapter="cointracking_csv",
                facts_path=facts_path,
                output_path=tmp_path / "cointracking.csv",
            )
        )


def _write_facts(tmp_path: Path) -> Path:
    path = tmp_path / "facts.csv"
    fact = TransactionFact(
        fact_id=TransactionId("txn-1"),
        source=SourceId("fixture"),
        adapter_id=AdapterId("structured_csv"),
        timestamp=datetime(2023, 8, 6, 10, 0, 0, tzinfo=UTC),
        account="Fixture",
        wallet="Primary",
        classification=FactClassification(
            economic_kind=EconomicKind.SPOT_TRADE,
            journal_intent=JournalIntent.ASSET_EXCHANGE,
            tax_treatment_code=TaxTreatmentCode.CAPITAL_EXCHANGE,
            projection_type=ProjectionType.TRADE,
        ),
        legs=(
            EconomicLeg(direction="in", asset=AssetSymbol("BTC"), amount=Decimal("1")),
            EconomicLeg(direction="out", asset=AssetSymbol("CAD"), amount=Decimal("10")),
        ),
        fee_legs=(EconomicLeg(direction="out", asset=AssetSymbol("CAD"), amount=Decimal("0.1")),),
        tx_hash="tx-1",
    )
    FilesystemFactRepository().write_facts(path, (fact,))
    return path
