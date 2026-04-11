from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from tallylot.adapters.outputs.cointracking_csv.projection import (
    _COINTRACKING_TYPE_LABELS,
    cointracking_row,
)
from tallylot.adapters.outputs.cointracking_csv.schema import COINTRACKING_HEADER
from tallylot.application.normalization import NormalizeRequest
from tallylot.application.outputs import RenderOutputRequest
from tallylot.application.resource_refs import to_resource_ref
from tallylot.domain.instruments import InstrumentId
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
from tallylot.domain.types import AdapterId, LocationId, SourceId, TransactionId
from tallylot.infrastructure.serialization.csv_io import read_rows
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from repo_support.capture_roots import materialize_capture_root
from tests.support.services import build_normalization_service, build_render_service


def test_cointracking_projection_mapping_covers_every_runtime_projection_hint() -> None:
    assert set(_COINTRACKING_TYPE_LABELS) == set(ProjectionHint)


def test_cointracking_output_matches_expected_schema_and_projection_mapping(
    structured_source_dir: Path,
    tmp_path: Path,
) -> None:
    raw_capture_root = materialize_capture_root(
        tmp_path, source="fixture_source", source_dir=structured_source_dir
    )
    artifacts = FilesystemArtifactStore()
    normalization = build_normalization_service(artifacts=artifacts)
    render = build_render_service()
    normalized_dir = tmp_path / "normalized"

    normalization.execute(
        NormalizeRequest(
            source="fixture_source",
            raw_capture_ref=to_resource_ref(raw_capture_root),
            normalized_output_ref=to_resource_ref(normalized_dir),
        )
    )
    output_path = tmp_path / "cointracking.csv"
    render.execute(
        RenderOutputRequest(
            output_adapter="cointracking_csv",
            facts_ref=to_resource_ref(normalized_dir / "facts.csv"),
            output_ref=to_resource_ref(output_path),
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
                _leg("primary_btc", LegKind.PRIMARY, "symbol:BTC", "1"),
                _leg("primary_cad", LegKind.PRIMARY, "symbol:CAD", "-10"),
                _leg(
                    "fee_cad",
                    LegKind.CHARGE,
                    "symbol:CAD",
                    "-0.1",
                    attributed_to_leg_id="primary_cad",
                ),
            ),
            leg_policy=TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
        )
    )

    assert row["Fee"] == "0.1"
    assert row["Cur..2"] == "symbol:CAD"


def test_cointracking_projection_uses_source_label_for_onchain_canonical_locations() -> (
    None
):
    row = cointracking_row(
        TransactionFact(
            fact_id=TransactionId("txn-onchain"),
            source=SourceId("polygon-wallet"),
            adapter_id=AdapterId("evm_explorer"),
            timestamp=datetime(2025, 1, 1, tzinfo=UTC),
            location_id=LocationId(
                "evm:polygon:0x1111111111111111111111111111111111111111"
            ),
            semantics=FactSemantics(
                economic_kind=EconomicKind.CHAIN_TRANSFER_IN,
                projection_hint=ProjectionHint.DEPOSIT,
                accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
                tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
            ),
            legs=(
                _leg("primary_bnb", LegKind.PRIMARY, "symbol:BNB@evm_explorer", "1"),
            ),
            leg_policy=FactLegPolicy(
                limits=(
                    LegShapeLimit(
                        kind=LegKind.PRIMARY, max_count=1, max_positive_count=1
                    ),
                )
            ),
        )
    )

    assert row["Exchange"] == "polygon-wallet"


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
                    _leg("primary_btc", LegKind.PRIMARY, "symbol:BTC", "1"),
                    _leg("primary_eth", LegKind.PRIMARY, "symbol:ETH", "2"),
                    _leg("primary_cad", LegKind.PRIMARY, "symbol:CAD", "-10"),
                ),
                leg_policy=FactLegPolicy(
                    limits=(
                        LegShapeLimit(
                            kind=LegKind.PRIMARY,
                            max_count=3,
                            max_positive_count=2,
                            max_negative_count=1,
                        ),
                        LegShapeLimit(
                            kind=LegKind.CHARGE,
                            max_count=1,
                            max_positive_count=0,
                            max_negative_count=1,
                        ),
                    )
                ),
            )
        )


def test_cointracking_projection_rejects_positive_charge_legs() -> None:
    with pytest.raises(ValueError, match="charge legs must be negative"):
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
                    _leg("primary_cad", LegKind.PRIMARY, "symbol:CAD", "-1"),
                    _leg(
                        "fee_cad",
                        LegKind.CHARGE,
                        "symbol:CAD",
                        "1",
                        attributed_to_leg_id="primary_cad",
                    ),
                ),
                leg_policy=FactLegPolicy(
                    limits=(
                        LegShapeLimit(
                            kind=LegKind.PRIMARY,
                            min_count=1,
                            max_count=1,
                            max_positive_count=0,
                            max_negative_count=1,
                        ),
                        LegShapeLimit(
                            kind=LegKind.CHARGE, max_count=1, max_positive_count=1
                        ),
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
                legs=(_leg("fee_cad", LegKind.CHARGE, "symbol:CAD", "-1"),),
                leg_policy=FactLegPolicy(
                    limits=(
                        LegShapeLimit(
                            kind=LegKind.CHARGE, max_count=1, max_negative_count=1
                        ),
                    )
                ),
            )
        )


def _leg(
    leg_id: str,
    kind: LegKind,
    instrument_id: str,
    quantity: str,
    *,
    attributed_to_leg_id: str | None = None,
) -> EconomicLeg:
    return EconomicLeg(
        leg_id=leg_id,
        kind=kind,
        instrument_id=InstrumentId(instrument_id),
        quantity=Decimal(quantity),
        attributed_to_leg_id=attributed_to_leg_id,
    )
