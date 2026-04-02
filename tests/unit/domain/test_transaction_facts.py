from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import cast

import pytest

from tallylot.domain.transactions import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
    AccountingIntentHint,
    EconomicKind,
    EconomicLeg,
    FactDirection,
    FactLegPolicy,
    FactSemantics,
    LegKind,
    LegShapeLimit,
    ProjectionHint,
    TaxTreatmentHint,
    TransactionFact,
)
from tallylot.domain.types import AdapterId, AssetSymbol, LocationId, SourceId, TransactionId
from tallylot.domain.value_objects import parse_timestamp


def _build_fact(
    *,
    legs: tuple[EconomicLeg, ...],
    leg_policy: FactLegPolicy = SINGLE_PRIMARY_ACTIVITY_POLICY,
) -> TransactionFact:
    return TransactionFact(
        fact_id=TransactionId("fact-1"),
        source=SourceId("fixture"),
        adapter_id=AdapterId("structured_csv"),
        timestamp=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        location_id=LocationId("taxable:spot"),
        semantics=FactSemantics(
            economic_kind=EconomicKind.SPOT_TRADE,
            projection_hint=ProjectionHint.TRADE,
            accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
            tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
        ),
        legs=legs,
        leg_policy=leg_policy,
        tx_hash="abc123",
    )


def test_transaction_fact_exposes_projection_properties_and_serializes_legs() -> None:
    fact = _build_fact(
        legs=(
            EconomicLeg(direction="in", kind=LegKind.PRIMARY, asset=AssetSymbol("BTC"), amount=Decimal("1.25")),
            EconomicLeg(direction="out", kind=LegKind.PRIMARY, asset=AssetSymbol("CAD"), amount=Decimal("100000")),
            EconomicLeg(
                direction="out",
                kind=LegKind.CHARGE,
                asset=AssetSymbol("CAD"),
                amount=Decimal("12.5"),
                attributed_to_direction="out",
                subtype="trading_fee",
            ),
        ),
        leg_policy=TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
    )

    assert fact.projection_hint == ProjectionHint.TRADE
    assert fact.leg_policy == TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY
    assert fact.legs[0].asset == AssetSymbol("BTC")
    assert fact.legs[1].amount == Decimal("100000")

    row = fact.to_row()

    assert row["fact_id"] == "fact-1"
    assert row["projection_hint"] == "trade"
    assert row["legs"] == (
        '[{"direction":"in","kind":"primary","subtype":"","asset":"BTC","amount":"1.25",'
        '"attributed_to_direction":"","location_id":""},'
        '{"direction":"out","kind":"primary","subtype":"","asset":"CAD","amount":"100000",'
        '"attributed_to_direction":"","location_id":""},'
        '{"direction":"out","kind":"charge","subtype":"trading_fee","asset":"CAD","amount":"12.5",'
        '"attributed_to_direction":"out","location_id":""}]'
    )
    assert row["leg_policy"] == (
        '[{"kind":"charge","min_count":0,"max_count":1,"min_in_count":null,"max_in_count":0,'
        '"min_out_count":null,"max_out_count":1},'
        '{"kind":"primary","min_count":2,"max_count":2,"min_in_count":1,"max_in_count":1,'
        '"min_out_count":1,"max_out_count":1}]'
    )


def test_transaction_fact_requires_at_least_one_leg() -> None:
    with pytest.raises(ValueError, match="include at least one leg"):
        _build_fact(legs=())


def test_fact_leg_rejects_non_positive_amounts() -> None:
    with pytest.raises(ValueError, match="fact leg amount must be greater than zero"):
        EconomicLeg(direction="in", kind=LegKind.PRIMARY, asset=AssetSymbol("BTC"), amount=Decimal("0"))


def test_fact_leg_rejects_invalid_direction_values() -> None:
    with pytest.raises(ValueError, match="unsupported fact leg direction: buy"):
        EconomicLeg(
            direction=cast(FactDirection, "buy"),
            kind=LegKind.PRIMARY,
            asset=AssetSymbol("BTC"),
            amount=Decimal("1"),
        )

    with pytest.raises(ValueError, match="unsupported fact leg attributed_to_direction: side"):
        EconomicLeg(
            direction="out",
            kind=LegKind.CHARGE,
            asset=AssetSymbol("CAD"),
            amount=Decimal("1"),
            attributed_to_direction=cast(FactDirection, "side"),
        )


def test_fact_leg_policy_rejects_invalid_limits() -> None:
    with pytest.raises(ValueError, match="min_count must be non-negative"):
        LegShapeLimit(kind=LegKind.PRIMARY, max_count=1, min_count=-1)

    with pytest.raises(ValueError, match="max_count must be non-negative"):
        LegShapeLimit(kind=LegKind.PRIMARY, max_count=-1)

    with pytest.raises(ValueError, match="min_count must not exceed max_count"):
        LegShapeLimit(kind=LegKind.PRIMARY, min_count=2, max_count=1)

    with pytest.raises(ValueError, match="min_in_count must not exceed max_in_count"):
        LegShapeLimit(kind=LegKind.PRIMARY, max_count=2, min_in_count=2, max_in_count=1)

    with pytest.raises(ValueError, match="min_out_count must not exceed max_out_count"):
        LegShapeLimit(kind=LegKind.PRIMARY, max_count=2, min_out_count=2, max_out_count=1)

    with pytest.raises(ValueError, match="directional minimum counts must not exceed max_count"):
        LegShapeLimit(kind=LegKind.PRIMARY, min_count=0, max_count=1, min_in_count=1, min_out_count=1)

    with pytest.raises(ValueError, match="duplicates kind primary"):
        FactLegPolicy(
            limits=(
                LegShapeLimit(kind=LegKind.PRIMARY, max_count=1),
                LegShapeLimit(kind=LegKind.PRIMARY, max_count=2),
            )
        )


def test_transaction_fact_rejects_legs_that_exceed_declared_policy() -> None:
    with pytest.raises(ValueError, match="inbound primary legs exceed declared leg policy"):
        _build_fact(
            legs=(
                EconomicLeg(direction="in", kind=LegKind.PRIMARY, asset=AssetSymbol("BTC"), amount=Decimal("1")),
                EconomicLeg(direction="in", kind=LegKind.PRIMARY, asset=AssetSymbol("ETH"), amount=Decimal("2")),
            ),
            leg_policy=FactLegPolicy(
                limits=(LegShapeLimit(kind=LegKind.PRIMARY, max_count=2, max_in_count=1, max_out_count=1),)
            ),
        )

    with pytest.raises(ValueError, match="charge legs exceed declared leg policy"):
        TransactionFact(
            fact_id=TransactionId("fact-2"),
            source=SourceId("fixture"),
            adapter_id=AdapterId("structured_csv"),
            timestamp=parse_timestamp("2025-01-01 00:00:00"),
            location_id=LocationId("taxable:spot"),
            semantics=FactSemantics(
                economic_kind=EconomicKind.PLATFORM_REWARD,
                accounting_intent_hint=AccountingIntentHint.INCOME_RECOGNITION,
                tax_treatment_hint=TaxTreatmentHint.ORDINARY_INCOME,
                projection_hint=None,
            ),
            legs=(
                EconomicLeg(direction="in", kind=LegKind.PRIMARY, asset=AssetSymbol("BTC"), amount=Decimal("0.5")),
                EconomicLeg(direction="out", kind=LegKind.CHARGE, asset=AssetSymbol("CAD"), amount=Decimal("1")),
                EconomicLeg(direction="out", kind=LegKind.CHARGE, asset=AssetSymbol("USD"), amount=Decimal("2")),
            ),
            leg_policy=FactLegPolicy(
                limits=(
                    LegShapeLimit(kind=LegKind.PRIMARY, max_count=1, max_in_count=1, max_out_count=1),
                    LegShapeLimit(kind=LegKind.CHARGE, max_count=1, max_in_count=0, max_out_count=1),
                )
            ),
        )


def test_transaction_fact_rejects_legs_that_fall_below_declared_policy() -> None:
    with pytest.raises(ValueError, match="primary legs fall below declared leg policy"):
        _build_fact(
            legs=(EconomicLeg(direction="out", kind=LegKind.CHARGE, asset=AssetSymbol("CAD"), amount=Decimal("1")),),
            leg_policy=TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
        )

    with pytest.raises(ValueError, match="outbound primary legs fall below declared leg policy"):
        _build_fact(
            legs=(EconomicLeg(direction="in", kind=LegKind.PRIMARY, asset=AssetSymbol("BTC"), amount=Decimal("1")),),
            leg_policy=FactLegPolicy(
                limits=(
                    LegShapeLimit(
                        kind=LegKind.PRIMARY,
                        min_count=1,
                        max_count=2,
                        min_out_count=1,
                        max_in_count=1,
                        max_out_count=1,
                    ),
                )
            ),
        )


def test_transaction_fact_accepts_explicit_multi_leg_policy_without_primary_requirement() -> None:
    fact = TransactionFact(
        fact_id=TransactionId("fact-2"),
        source=SourceId("fixture"),
        adapter_id=AdapterId("structured_csv"),
        timestamp=parse_timestamp("2025-01-01 00:00:00"),
        location_id=LocationId("taxable:spot"),
        semantics=FactSemantics(
            economic_kind=EconomicKind.PLATFORM_REWARD,
            accounting_intent_hint=AccountingIntentHint.INCOME_RECOGNITION,
            tax_treatment_hint=TaxTreatmentHint.ORDINARY_INCOME,
            projection_hint=None,
        ),
        legs=(
            EconomicLeg(direction="in", kind=LegKind.REBATE, asset=AssetSymbol("BTC"), amount=Decimal("0.5")),
            EconomicLeg(direction="in", kind=LegKind.REBATE, asset=AssetSymbol("ETH"), amount=Decimal("1.5")),
            EconomicLeg(direction="out", kind=LegKind.WITHHOLDING, asset=AssetSymbol("CAD"), amount=Decimal("100")),
        ),
        leg_policy=FactLegPolicy(
            limits=(
                LegShapeLimit(kind=LegKind.REBATE, max_count=2, max_in_count=2, max_out_count=0),
                LegShapeLimit(kind=LegKind.WITHHOLDING, max_count=1, max_in_count=0, max_out_count=1),
            )
        ),
    )

    assert fact.projection_hint is None
    assert fact.leg_policy.limit_for(LegKind.REBATE) is not None


def test_transaction_fact_requires_utc_timestamp() -> None:
    with pytest.raises(ValueError, match="transaction fact timestamp must be timezone-aware UTC"):
        TransactionFact(
            fact_id=TransactionId("fact-utc"),
            source=SourceId("fixture"),
            adapter_id=AdapterId("structured_csv"),
            timestamp=datetime.fromisoformat("2025-01-01T00:00:00"),
            location_id=LocationId("taxable:spot"),
            semantics=FactSemantics(
                economic_kind=EconomicKind.CHAIN_TRANSFER_IN,
                accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
                tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
                projection_hint=ProjectionHint.DEPOSIT,
            ),
            legs=(EconomicLeg(direction="in", kind=LegKind.PRIMARY, asset=AssetSymbol("BTC"), amount=Decimal("1")),),
            leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
        )


def test_transaction_fact_rejects_ambiguous_attributed_to_direction() -> None:
    with pytest.raises(ValueError, match="attributed_to_direction must reference exactly one primary leg"):
        TransactionFact(
            fact_id=TransactionId("fact-3"),
            source=SourceId("fixture"),
            adapter_id=AdapterId("structured_csv"),
            timestamp=parse_timestamp("2025-01-01 00:00:00"),
            location_id=LocationId("taxable:spot"),
            semantics=FactSemantics(
                economic_kind=EconomicKind.SPOT_TRADE,
                accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
                tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
                projection_hint=ProjectionHint.TRADE,
            ),
            legs=(
                EconomicLeg(direction="in", kind=LegKind.PRIMARY, asset=AssetSymbol("BTC"), amount=Decimal("1")),
                EconomicLeg(direction="in", kind=LegKind.PRIMARY, asset=AssetSymbol("ETH"), amount=Decimal("2")),
                EconomicLeg(
                    direction="out",
                    kind=LegKind.CHARGE,
                    asset=AssetSymbol("CAD"),
                    amount=Decimal("10"),
                    attributed_to_direction="in",
                ),
            ),
            leg_policy=FactLegPolicy(
                limits=(
                    LegShapeLimit(kind=LegKind.PRIMARY, max_count=2, max_in_count=2, max_out_count=0),
                    LegShapeLimit(kind=LegKind.CHARGE, max_count=1, max_in_count=0, max_out_count=1),
                )
            ),
        )
