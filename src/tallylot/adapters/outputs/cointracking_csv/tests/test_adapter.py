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
from tallylot.infrastructure.serialization.csv_io import read_rows
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tests.support.services import build_normalization_service, build_render_service


def test_cointracking_projection_mapping_covers_every_runtime_projection_hint() -> None:
    assert set(COINTRACKING_TYPE_LABELS) == set(ProjectionHint)


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
    assert {row["projection_hint"] for row in fact_rows} == {"reward_bonus", "trade"}
    assert {row["Type"] for row in rows} == {"Reward / Bonus", "Trade"}
    assert not (normalized_dir / "cointracking_candidate.csv").exists()


def test_cointracking_projection_reads_standard_fee_leg() -> None:
    row = cointracking_row(
        TransactionFact(
            fact_id=TransactionId("txn-1"),
            source=SourceId("fixture"),
            adapter_id=AdapterId("fixture"),
            timestamp=datetime(2025, 1, 1, tzinfo=UTC),
            location_id=LocationId("fixture:primary"),
            semantics=FactSemantics(
                economic_kind=EconomicKind.SPOT_TRADE,
                projection_hint=ProjectionHint.TRADE,
                accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
                tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
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
                location_id=LocationId("fixture:primary"),
                semantics=FactSemantics(
                    economic_kind=EconomicKind.SPOT_TRADE,
                    projection_hint=ProjectionHint.TRADE,
                    accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
                    tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
                ),
                legs=(
                    EconomicLeg(direction="in", kind=LegKind.PRIMARY, asset=AssetSymbol("BTC"), amount=Decimal("1")),
                    EconomicLeg(direction="in", kind=LegKind.PRIMARY, asset=AssetSymbol("ETH"), amount=Decimal("2")),
                    EconomicLeg(direction="out", kind=LegKind.PRIMARY, asset=AssetSymbol("CAD"), amount=Decimal("10")),
                ),
                leg_policy=FactLegPolicy(
                    limits=(
                        LegShapeLimit(kind=LegKind.PRIMARY, max_count=3, max_in_count=2, max_out_count=1),
                        LegShapeLimit(kind=LegKind.CHARGE, max_count=1, max_in_count=0, max_out_count=1),
                    )
                ),
            )
        )


def test_cointracking_projection_rejects_inbound_charge_legs() -> None:
    with pytest.raises(ValueError, match="charge legs must be outbound"):
        cointracking_row(
            TransactionFact(
                fact_id=TransactionId("txn-3"),
                source=SourceId("fixture"),
                adapter_id=AdapterId("fixture"),
                timestamp=datetime(2025, 1, 1, tzinfo=UTC),
                location_id=LocationId("fixture:primary"),
                semantics=FactSemantics(
                    economic_kind=EconomicKind.CASH_EXPENSE,
                    projection_hint=ProjectionHint.EXPENSE_NON_TAXABLE,
                    accounting_intent_hint=AccountingIntentHint.EXPENSE_RECOGNITION,
                    tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_EXPENSE,
                ),
                legs=(
                    EconomicLeg(direction="out", kind=LegKind.PRIMARY, asset=AssetSymbol("CAD"), amount=Decimal("1")),
                    EconomicLeg(direction="in", kind=LegKind.CHARGE, asset=AssetSymbol("CAD"), amount=Decimal("1")),
                ),
                leg_policy=FactLegPolicy(
                    limits=(
                        LegShapeLimit(kind=LegKind.PRIMARY, min_count=1, max_count=1, max_in_count=0, max_out_count=1),
                        LegShapeLimit(kind=LegKind.CHARGE, max_count=1, max_in_count=1),
                    )
                ),
            )
        )


def test_cointracking_projection_rejects_fee_only_shapes() -> None:
    with pytest.raises(ValueError, match="expected at least one primary leg"):
        cointracking_row(
            TransactionFact(
                fact_id=TransactionId("txn-4"),
                source=SourceId("fixture"),
                adapter_id=AdapterId("fixture"),
                timestamp=datetime(2025, 1, 1, tzinfo=UTC),
                location_id=LocationId("fixture:primary"),
                semantics=FactSemantics(
                    economic_kind=EconomicKind.CASH_EXPENSE,
                    projection_hint=ProjectionHint.EXPENSE_NON_TAXABLE,
                    accounting_intent_hint=AccountingIntentHint.EXPENSE_RECOGNITION,
                    tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_EXPENSE,
                ),
                legs=(
                    EconomicLeg(direction="out", kind=LegKind.CHARGE, asset=AssetSymbol("CAD"), amount=Decimal("1")),
                ),
                leg_policy=FactLegPolicy(limits=(LegShapeLimit(kind=LegKind.CHARGE, max_count=1, max_out_count=1),)),
            )
        )
