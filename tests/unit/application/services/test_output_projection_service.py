from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from crypto_reconciliation.application.models.output import RenderOutputRequest
from crypto_reconciliation.application.services.projections import OutputProjectionService
from crypto_reconciliation.domain.models import AdapterCapability, AdapterManifest
from crypto_reconciliation.domain.models.transactions import NormalizedTransaction
from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId
from crypto_reconciliation.infrastructure.serialization.csv_io import write_rows
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from crypto_reconciliation.ports.adapters import OutputAdapter, RenderedArtifact
from crypto_reconciliation.ports.artifacts import ArtifactStorePort
from crypto_reconciliation.ports.output_workflows import BaselineArtifacts, ScreeningResult


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

    def render(self, transactions: tuple[NormalizedTransaction, ...], output_path: Path) -> RenderedArtifact:
        del transactions, output_path
        raise AssertionError("render should not be called when adapter validation fails")

    def candidate_artifact_name(self) -> str:
        return "cointracking_candidate.csv"

    def match_candidate(self, candidate_path: Path, artifacts: ArtifactStorePort) -> int:
        del candidate_path, artifacts
        return 0

    def screen_candidate(
        self,
        candidate_path: Path,
        baseline_export_dir: Path,
        artifacts: ArtifactStorePort,
    ) -> ScreeningResult:
        del candidate_path, baseline_export_dir, artifacts
        raise AssertionError("screen_candidate should not be called in render tests")

    def match_baseline_exports(self, export_dir: Path, artifacts: ArtifactStorePort) -> int:
        del export_dir, artifacts
        return 0

    def build_baseline_artifacts(self, export_dir: Path, artifacts: ArtifactStorePort) -> BaselineArtifacts:
        del export_dir, artifacts
        raise AssertionError("build_baseline_artifacts should not be called in render tests")


def test_output_projection_service_rejects_unsupported_output_adapters(tmp_path: Path) -> None:
    transactions_path = _write_transactions(tmp_path)
    service = OutputProjectionService(
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
            RenderOutputRequest(
                output_adapter="cointracking_csv",
                transactions_path=transactions_path,
                output_path=tmp_path / "cointracking.csv",
            )
        )


def test_output_projection_service_rejects_adapters_without_render_capability(tmp_path: Path) -> None:
    transactions_path = _write_transactions(tmp_path)
    service = OutputProjectionService(
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
            RenderOutputRequest(
                output_adapter="cointracking_csv",
                transactions_path=transactions_path,
                output_path=tmp_path / "cointracking.csv",
            )
        )


def _write_transactions(tmp_path: Path) -> Path:
    path = tmp_path / "transactions.csv"
    row = NormalizedTransaction(
        transaction_id=TransactionId("txn-1"),
        source=SourceId("fixture"),
        adapter_id=AdapterId("structured_csv"),
        account="Fixture",
        wallet="Primary",
        timestamp=datetime(2023, 8, 6, 10, 0, 0, tzinfo=UTC),
        category="trade",
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
