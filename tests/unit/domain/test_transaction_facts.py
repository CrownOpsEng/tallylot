from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from tallylot.domain.instruments import InstrumentId
from tallylot.domain.transactions import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
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


def _leg(
    leg_id: str,
    instrument_id: str,
    quantity: str,
    *,
    kind: LegKind = LegKind.PRIMARY,
    subtype: str | None = None,
    attributed_to_leg_id: str | None = None,
) -> EconomicLeg:
    return EconomicLeg(
        leg_id=leg_id,
        kind=kind,
        instrument_id=InstrumentId(instrument_id),
        quantity=Decimal(quantity),
        subtype=subtype,
        attributed_to_leg_id=attributed_to_leg_id,
    )


def test_transaction_fact_exposes_projection_properties_and_serializes_legs() -> None:
    fact = _build_fact(
        legs=(
            _leg("primary_btc", "symbol:BTC", "1.25"),
            _leg("primary_cad", "symbol:CAD", "-100000"),
            _leg(
                "fee_cad",
                "symbol:CAD",
                "-12.5",
                kind=LegKind.CHARGE,
                attributed_to_leg_id="primary_cad",
                subtype="trading_fee",
            ),
        ),
        leg_policy=TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
    )

    assert fact.projection_hint == ProjectionHint.TRADE
    assert fact.leg_policy == TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY
    assert fact.legs[0].instrument_id == InstrumentId("symbol:BTC")
    assert fact.legs[1].quantity == Decimal("-100000")

    row = fact.to_row()

    assert row["schema_version"] == "2"
    assert row["fact_id"] == "fact-1"
    assert row["projection_hint"] == "trade"
    assert row["legs"] == (
        '[{"leg_id":"primary_btc","kind":"primary","subtype":"","instrument_id":"symbol:BTC","quantity":"1.25",'
        '"attributed_to_leg_id":"","location_id":""},'
        '{"leg_id":"primary_cad","kind":"primary","subtype":"","instrument_id":"symbol:CAD","quantity":"-100000",'
        '"attributed_to_leg_id":"","location_id":""},'
        '{"leg_id":"fee_cad","kind":"charge","subtype":"trading_fee","instrument_id":"symbol:CAD","quantity":"-12.5",'
        '"attributed_to_leg_id":"primary_cad","location_id":""}]'
    )
    assert row["leg_policy"] == (
        '[{"kind":"charge","min_count":0,"max_count":1,"min_positive_count":null,"max_positive_count":0,'
        '"min_negative_count":null,"max_negative_count":1},'
        '{"kind":"primary","min_count":2,"max_count":2,"min_positive_count":1,"max_positive_count":1,'
        '"min_negative_count":1,"max_negative_count":1}]'
    )


def test_transaction_fact_requires_at_least_one_leg() -> None:
    with pytest.raises(ValueError, match="include at least one leg"):
        _build_fact(legs=())


def test_fact_leg_rejects_zero_quantity() -> None:
    with pytest.raises(ValueError, match="fact leg quantity must not be zero"):
        _leg("primary_btc", "symbol:BTC", "0")


def test_fact_leg_rejects_invalid_leg_metadata() -> None:
    with pytest.raises(ValueError, match="fact leg_id must be lowercase snake_case"):
        _leg("PrimaryBTC", "symbol:BTC", "1")

    with pytest.raises(
        ValueError, match="fact leg attributed_to_leg_id must be lowercase snake_case"
    ):
        EconomicLeg(
            leg_id="fee_cad",
            kind=LegKind.CHARGE,
            instrument_id=InstrumentId("symbol:CAD"),
            quantity=Decimal("-1"),
            attributed_to_leg_id="PrimaryCad",
        )


def test_fact_leg_policy_rejects_invalid_limits() -> None:
    with pytest.raises(ValueError, match="min_count must be non-negative"):
        LegShapeLimit(kind=LegKind.PRIMARY, max_count=1, min_count=-1)

    with pytest.raises(ValueError, match="max_count must be non-negative"):
        LegShapeLimit(kind=LegKind.PRIMARY, max_count=-1)

    with pytest.raises(ValueError, match="min_count must not exceed max_count"):
        LegShapeLimit(kind=LegKind.PRIMARY, min_count=2, max_count=1)

    with pytest.raises(
        ValueError, match="min_positive_count must not exceed max_positive_count"
    ):
        LegShapeLimit(
            kind=LegKind.PRIMARY,
            max_count=2,
            min_positive_count=2,
            max_positive_count=1,
        )

    with pytest.raises(
        ValueError, match="min_negative_count must not exceed max_negative_count"
    ):
        LegShapeLimit(
            kind=LegKind.PRIMARY,
            max_count=2,
            min_negative_count=2,
            max_negative_count=1,
        )

    with pytest.raises(
        ValueError, match="signed minimum counts must not exceed max_count"
    ):
        LegShapeLimit(
            kind=LegKind.PRIMARY,
            min_count=0,
            max_count=1,
            min_positive_count=1,
            min_negative_count=1,
        )

    with pytest.raises(ValueError, match="duplicates kind primary"):
        FactLegPolicy(
            limits=(
                LegShapeLimit(kind=LegKind.PRIMARY, max_count=1),
                LegShapeLimit(kind=LegKind.PRIMARY, max_count=2),
            )
        )


def test_transaction_fact_rejects_legs_that_exceed_declared_policy() -> None:
    with pytest.raises(
        ValueError, match="positive primary legs exceed declared leg policy"
    ):
        _build_fact(
            legs=(
                _leg("primary_btc", "symbol:BTC", "1"),
                _leg("primary_eth", "symbol:ETH", "2"),
            ),
            leg_policy=FactLegPolicy(
                limits=(
                    LegShapeLimit(
                        kind=LegKind.PRIMARY,
                        max_count=2,
                        max_positive_count=1,
                        max_negative_count=1,
                    ),
                )
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
                _leg("rebate_btc", "symbol:BTC", "0.5"),
                _leg(
                    "fee_cad",
                    "symbol:CAD",
                    "-1",
                    kind=LegKind.CHARGE,
                    attributed_to_leg_id="rebate_btc",
                ),
                _leg(
                    "fee_usd",
                    "symbol:USD",
                    "-2",
                    kind=LegKind.CHARGE,
                    attributed_to_leg_id="rebate_btc",
                ),
            ),
            leg_policy=FactLegPolicy(
                limits=(
                    LegShapeLimit(
                        kind=LegKind.PRIMARY,
                        max_count=1,
                        max_positive_count=1,
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


def test_transaction_fact_rejects_legs_that_fall_below_declared_policy() -> None:
    with pytest.raises(ValueError, match="primary legs fall below declared leg policy"):
        _build_fact(
            legs=(
                _leg(
                    "fee_cad",
                    "symbol:CAD",
                    "-1",
                    kind=LegKind.CHARGE,
                    attributed_to_leg_id="primary_btc",
                ),
            ),
            leg_policy=TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
        )

    with pytest.raises(
        ValueError, match="negative primary legs fall below declared leg policy"
    ):
        _build_fact(
            legs=(_leg("primary_btc", "symbol:BTC", "1"),),
            leg_policy=FactLegPolicy(
                limits=(
                    LegShapeLimit(
                        kind=LegKind.PRIMARY,
                        min_count=1,
                        max_count=2,
                        min_negative_count=1,
                        max_positive_count=1,
                        max_negative_count=1,
                    ),
                )
            ),
        )


def test_transaction_fact_accepts_explicit_multi_leg_policy_without_primary_requirement() -> (
    None
):
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
            _leg("rebate_btc", "symbol:BTC", "0.5", kind=LegKind.REBATE),
            _leg("rebate_eth", "symbol:ETH", "1.5", kind=LegKind.REBATE),
            _leg("withholding_cad", "symbol:CAD", "-100", kind=LegKind.WITHHOLDING),
        ),
        leg_policy=FactLegPolicy(
            limits=(
                LegShapeLimit(
                    kind=LegKind.REBATE,
                    max_count=2,
                    max_positive_count=2,
                    max_negative_count=0,
                ),
                LegShapeLimit(
                    kind=LegKind.WITHHOLDING,
                    max_count=1,
                    max_positive_count=0,
                    max_negative_count=1,
                ),
            )
        ),
    )

    assert fact.projection_hint is None
    assert fact.leg_policy.limit_for(LegKind.REBATE) is not None


def test_transaction_fact_requires_utc_timestamp() -> None:
    with pytest.raises(
        ValueError, match="transaction fact timestamp must be timezone-aware UTC"
    ):
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
            legs=(_leg("primary_btc", "symbol:BTC", "1"),),
            leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
        )


def test_transaction_fact_rejects_ambiguous_attributed_to_leg_id() -> None:
    with pytest.raises(
        ValueError,
        match="attributed_to_leg_id must reference one primary leg in the same fact",
    ):
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
                _leg("primary_btc", "symbol:BTC", "1"),
                _leg("primary_eth", "symbol:ETH", "2"),
                _leg(
                    "fee_cad",
                    "symbol:CAD",
                    "-10",
                    kind=LegKind.CHARGE,
                    attributed_to_leg_id="missing_leg",
                ),
            ),
            leg_policy=FactLegPolicy(
                limits=(
                    LegShapeLimit(
                        kind=LegKind.PRIMARY,
                        max_count=2,
                        max_positive_count=2,
                        max_negative_count=0,
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
