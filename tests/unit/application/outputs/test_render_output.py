from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from tallylot.application.outputs import RenderOutputRequest, RenderOutputUseCase
from tallylot.application.resource_refs import to_resource_ref
from tallylot.domain.transactions import (
    TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
    AccountingIntentHint,
    EconomicKind,
    EconomicLeg,
    FactLegPolicy,
    FactSemantics,
    LegKind,
    LegShapeLimit,
    ProjectionHint,
    TaxTreatmentHint,
    TransactionFact,
)
from tallylot.domain.types import AdapterId, AssetSymbol, LocationId, SourceId, TransactionId
from tallylot.infrastructure.storage import FilesystemFactRepository
from tallylot.ports.adapter_contracts import AdapterCapability, AdapterManifest
from tallylot.ports.output_adapters import OutputAdapter, OutputRenderPolicy, RenderedArtifact


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
        self.render_policy = OutputRenderPolicy(
            shape_policy=FactLegPolicy(
                limits=(
                    LegShapeLimit(kind=LegKind.PRIMARY, max_count=0, max_in_count=0, max_out_count=0),
                    LegShapeLimit(kind=LegKind.CHARGE, max_count=1, max_in_count=0, max_out_count=1),
                )
            ),
            requires_projection_hint=False,
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
                facts_ref=to_resource_ref(facts_path),
                output_ref=to_resource_ref(tmp_path / "cointracking.csv"),
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
                facts_ref=to_resource_ref(facts_path),
                output_ref=to_resource_ref(tmp_path / "cointracking.csv"),
            )
        )


def test_output_projection_service_rejects_facts_outside_render_policy(tmp_path: Path) -> None:
    facts_path = _write_facts(tmp_path)
    service = RenderOutputUseCase(
        FakeOutputRegistry(
            FakeOutputAdapter(
                supported=True,
                capabilities=frozenset({AdapterCapability.OUTPUT_RENDER}),
            )
        ),
        FilesystemFactRepository(),
    )

    with pytest.raises(ValueError, match="exceeds cointracking_csv render policy for primary legs"):
        service.execute(
            RenderOutputRequest(
                output_adapter="cointracking_csv",
                facts_ref=to_resource_ref(facts_path),
                output_ref=to_resource_ref(tmp_path / "cointracking.csv"),
            )
        )


def _write_facts(tmp_path: Path) -> Path:
    path = tmp_path / "facts.csv"
    fact = TransactionFact(
        fact_id=TransactionId("txn-1"),
        source=SourceId("fixture"),
        adapter_id=AdapterId("structured_csv"),
        timestamp=datetime(2023, 8, 6, 10, 0, 0, tzinfo=UTC),
        location_id=LocationId("fixture:primary"),
        semantics=FactSemantics(
            economic_kind=EconomicKind.SPOT_TRADE,
            accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
            tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
            projection_hint=ProjectionHint.TRADE,
        ),
        legs=(
            EconomicLeg(direction="in", kind=LegKind.PRIMARY, asset=AssetSymbol("BTC"), amount=Decimal("1")),
            EconomicLeg(direction="out", kind=LegKind.PRIMARY, asset=AssetSymbol("CAD"), amount=Decimal("10")),
            EconomicLeg(
                direction="out",
                kind=LegKind.CHARGE,
                asset=AssetSymbol("CAD"),
                amount=Decimal("0.1"),
                attributed_to_direction="out",
            ),
        ),
        leg_policy=TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
        tx_hash="tx-1",
    )
    FilesystemFactRepository().write_facts(path, (fact,))
    return path
