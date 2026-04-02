from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from tallylot.adapters.outputs.cointracking_csv import COINTRACKING_HEADER
from tallylot.adapters.outputs.cointracking_csv.projection import COINTRACKING_TYPE_LABELS, cointracking_row
from tallylot.application.normalization import NormalizeRequest
from tallylot.application.outputs import RenderOutputRequest
from tallylot.domain.transactions import (
    EconomicKind,
    EconomicLeg,
    FactClassification,
    FactLegPolicy,
    JournalIntent,
    ProjectionType,
    TaxTreatmentCode,
    TransactionFact,
)
from tallylot.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId
from tallylot.infrastructure.serialization.csv_io import read_rows
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tests.support.services import build_normalization_service, build_render_service


def test_cointracking_projection_mapping_covers_every_runtime_projection_type() -> None:
    assert set(COINTRACKING_TYPE_LABELS) == set(ProjectionType)


def test_cointracking_output_matches_expected_schema_and_projection_mapping(
    structured_source_dir: Path,
    tmp_path: Path,
) -> None:
    artifacts = FilesystemArtifactStore()
    normalization = build_normalization_service(artifacts=artifacts)
    render = build_render_service()
    normalized_dir = tmp_path / "normalized"

    normalization.execute(
        NormalizeRequest(
            source="fixture_source",
            raw_dir=structured_source_dir,
            output_dir=normalized_dir,
        )
    )
    output_path = tmp_path / "cointracking.csv"
    render.execute(
        RenderOutputRequest(
            output_adapter="cointracking_csv",
            facts_path=normalized_dir / "facts.csv",
            output_path=output_path,
        )
    )

    rows = read_rows(output_path)
    fact_rows = artifacts.read_rows(normalized_dir / "facts.csv")

    assert tuple(rows[0]) == COINTRACKING_HEADER
    assert len(rows) == 2
    assert {row["projection_type"] for row in fact_rows} == {"reward_bonus", "trade"}
    assert {row["Type"] for row in rows} == {"Reward / Bonus", "Trade"}
    assert not (normalized_dir / "cointracking_candidate.csv").exists()


def test_cointracking_projection_reads_standard_fee_leg() -> None:
    row = cointracking_row(
        TransactionFact(
            fact_id=TransactionId("txn-1"),
            source=SourceId("fixture"),
            adapter_id=AdapterId("fixture"),
            timestamp=datetime(2025, 1, 1, tzinfo=UTC),
            account="Fixture",
            wallet="Primary",
            classification=FactClassification(
                economic_kind=EconomicKind.SPOT_TRADE,
                projection_type=ProjectionType.TRADE,
                journal_intent=JournalIntent.ASSET_EXCHANGE,
                tax_treatment_code=TaxTreatmentCode.CAPITAL_EXCHANGE,
            ),
            legs=(
                EconomicLeg(direction="in", asset=AssetSymbol("BTC"), amount=Decimal("1")),
                EconomicLeg(direction="out", asset=AssetSymbol("CAD"), amount=Decimal("10")),
            ),
            fee_legs=(EconomicLeg(direction="out", asset=AssetSymbol("CAD"), amount=Decimal("0.1")),),
        )
    )

    assert row["Fee"] == "0.1"
    assert row["Cur..2"] == "CAD"


def test_cointracking_projection_rejects_unsupported_multi_leg_shapes() -> None:
    with pytest.raises(ValueError, match="unsupported CoinTracking projection shape"):
        cointracking_row(
            TransactionFact(
                fact_id=TransactionId("txn-2"),
                source=SourceId("fixture"),
                adapter_id=AdapterId("fixture"),
                timestamp=datetime(2025, 1, 1, tzinfo=UTC),
                account="Fixture",
                wallet="Primary",
                classification=FactClassification(
                    economic_kind=EconomicKind.SPOT_TRADE,
                    projection_type=ProjectionType.TRADE,
                    journal_intent=JournalIntent.ASSET_EXCHANGE,
                    tax_treatment_code=TaxTreatmentCode.CAPITAL_EXCHANGE,
                ),
                legs=(
                    EconomicLeg(direction="in", asset=AssetSymbol("BTC"), amount=Decimal("1")),
                    EconomicLeg(direction="in", asset=AssetSymbol("ETH"), amount=Decimal("2")),
                    EconomicLeg(direction="out", asset=AssetSymbol("CAD"), amount=Decimal("10")),
                ),
                leg_policy=FactLegPolicy(max_in_legs=2, max_out_legs=1, max_fee_legs=1),
            )
        )
