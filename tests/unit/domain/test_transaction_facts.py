from __future__ import annotations

from decimal import Decimal

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
from crypto_reconciliation.domain.value_objects import parse_timestamp


def test_transaction_fact_exposes_projection_properties_and_serializes_legs() -> None:
    fact = TransactionFact(
        fact_id=TransactionId("fact-1"),
        source=SourceId("fixture"),
        adapter_id=AdapterId("structured_csv"),
        timestamp=parse_timestamp("2025-01-01 00:00:00"),
        account="taxable",
        wallet="spot",
        classification=FactClassification(
            economic_kind=EconomicKind.SPOT_TRADE,
            projection_type=ProjectionType.TRADE,
            journal_intent=JournalIntent.ASSET_EXCHANGE,
            tax_treatment_code=TaxTreatmentCode.CAPITAL_EXCHANGE,
        ),
        legs=(
            EconomicLeg(direction="in", asset=AssetSymbol("BTC"), amount=Decimal("1.25")),
            EconomicLeg(direction="out", asset=AssetSymbol("CAD"), amount=Decimal("100000")),
        ),
        fee_legs=(EconomicLeg(direction="out", asset=AssetSymbol("CAD"), amount=Decimal("12.5")),),
        tx_hash="abc123",
    )

    assert fact.category == "trade"
    assert fact.asset_in == AssetSymbol("BTC")
    assert fact.amount_out == Decimal("100000")

    row = fact.to_row()

    assert row["fact_id"] == "fact-1"
    assert row["projection_type"] == "Trade"
    assert row["legs"] == "in:BTC:1.25::|out:CAD:100000::"
    assert row["fee_legs"] == "out:CAD:12.5::"
