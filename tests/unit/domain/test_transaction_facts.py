from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

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
from tallylot.domain.value_objects import parse_timestamp


def _build_fact(*, legs: tuple[EconomicLeg, ...], fee_legs: tuple[EconomicLeg, ...] = ()) -> TransactionFact:
    return TransactionFact(
        fact_id=TransactionId("fact-1"),
        source=SourceId("fixture"),
        adapter_id=AdapterId("structured_csv"),
        timestamp=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        account="taxable",
        wallet="spot",
        classification=FactClassification(
            economic_kind=EconomicKind.SPOT_TRADE,
            projection_type=ProjectionType.TRADE,
            journal_intent=JournalIntent.ASSET_EXCHANGE,
            tax_treatment_code=TaxTreatmentCode.CAPITAL_EXCHANGE,
        ),
        legs=legs,
        fee_legs=fee_legs,
        tx_hash="abc123",
    )


def test_transaction_fact_exposes_projection_properties_and_serializes_legs() -> None:
    fact = _build_fact(
        legs=(
            EconomicLeg(direction="in", asset=AssetSymbol("BTC"), amount=Decimal("1.25")),
            EconomicLeg(direction="out", asset=AssetSymbol("CAD"), amount=Decimal("100000")),
        ),
        fee_legs=(EconomicLeg(direction="out", asset=AssetSymbol("CAD"), amount=Decimal("12.5")),),
    )

    assert fact.projection_type == ProjectionType.TRADE
    assert fact.leg_policy == FactLegPolicy()
    assert fact.legs[0].asset == AssetSymbol("BTC")
    assert fact.legs[1].amount == Decimal("100000")

    row = fact.to_row()

    assert row["fact_id"] == "fact-1"
    assert row["max_in_legs"] == "1"
    assert row["max_out_legs"] == "1"
    assert row["max_fee_legs"] == "1"
    assert row["projection_type"] == "trade"
    assert row["legs"] == "in:BTC:1.25::|out:CAD:100000::"
    assert row["fee_legs"] == "out:CAD:12.5::"


def test_transaction_fact_requires_at_least_one_leg() -> None:
    with pytest.raises(ValueError, match="at least one economic leg"):
        _build_fact(legs=())


def test_fact_leg_rejects_non_positive_amounts() -> None:
    with pytest.raises(ValueError, match="fact leg amount must be greater than zero"):
        EconomicLeg(direction="in", asset=AssetSymbol("BTC"), amount=Decimal("0"))


def test_fact_leg_policy_rejects_negative_limits() -> None:
    with pytest.raises(ValueError, match="max_in_legs must be non-negative"):
        FactLegPolicy(max_in_legs=-1)


def test_transaction_fact_rejects_legs_that_exceed_declared_policy() -> None:
    with pytest.raises(ValueError, match="inbound legs exceed declared leg policy"):
        _build_fact(
            legs=(
                EconomicLeg(direction="in", asset=AssetSymbol("BTC"), amount=Decimal("1")),
                EconomicLeg(direction="in", asset=AssetSymbol("ETH"), amount=Decimal("2")),
            ),
            fee_legs=(),
        )

    with pytest.raises(ValueError, match="fee legs exceed declared leg policy"):
        TransactionFact(
            fact_id=TransactionId("fact-2"),
            source=SourceId("fixture"),
            adapter_id=AdapterId("structured_csv"),
            timestamp=parse_timestamp("2025-01-01 00:00:00"),
            account="taxable",
            wallet="spot",
            classification=FactClassification(
                economic_kind=EconomicKind.PLATFORM_REWARD,
                journal_intent=JournalIntent.INCOME_RECOGNITION,
                tax_treatment_code=TaxTreatmentCode.ORDINARY_INCOME,
                projection_type=None,
            ),
            legs=(EconomicLeg(direction="in", asset=AssetSymbol("BTC"), amount=Decimal("0.5")),),
            fee_legs=(
                EconomicLeg(direction="out", asset=AssetSymbol("CAD"), amount=Decimal("1")),
                EconomicLeg(direction="out", asset=AssetSymbol("USD"), amount=Decimal("2")),
            ),
        )


def test_transaction_fact_accepts_explicit_multi_leg_policy() -> None:
    fact = TransactionFact(
        fact_id=TransactionId("fact-2"),
        source=SourceId("fixture"),
        adapter_id=AdapterId("structured_csv"),
        timestamp=parse_timestamp("2025-01-01 00:00:00"),
        account="taxable",
        wallet="spot",
        classification=FactClassification(
            economic_kind=EconomicKind.PLATFORM_REWARD,
            journal_intent=JournalIntent.INCOME_RECOGNITION,
            tax_treatment_code=TaxTreatmentCode.ORDINARY_INCOME,
            projection_type=None,
        ),
        legs=(
            EconomicLeg(direction="in", asset=AssetSymbol("BTC"), amount=Decimal("0.5")),
            EconomicLeg(direction="in", asset=AssetSymbol("ETH"), amount=Decimal("1.5")),
            EconomicLeg(direction="out", asset=AssetSymbol("CAD"), amount=Decimal("100")),
        ),
        leg_policy=FactLegPolicy(max_in_legs=2, max_out_legs=1, max_fee_legs=0),
    )

    assert fact.projection_type is None
    assert fact.leg_policy.max_in_legs == 2
