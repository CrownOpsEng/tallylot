from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.transactions import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
    AccountingIntentHint,
    EconomicKind,
    FactLegPolicy,
    LegKind,
    LegShapeLimit,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.domain.types import LocationId
from tallylot.ports.source_translation import (
    ActivityDraftSeed,
    EconomicActivityDraft,
    classification,
    economic_leg,
)


def test_activity_draft_seed_requires_explicit_leg_policy() -> None:
    seed = ActivityDraftSeed(
        activity_id="txn-1",
        timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
    )

    assert seed.leg_policy == SINGLE_PRIMARY_ACTIVITY_POLICY


def test_activity_draft_seed_requires_utc_timestamp() -> None:
    with pytest.raises(
        ValueError, match="activity draft seed timestamp must be timezone-aware UTC"
    ):
        ActivityDraftSeed(
            activity_id="txn-1",
            timestamp=datetime.fromisoformat("2025-01-01T00:00:00"),
            leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
        )


def test_activity_draft_seed_requires_complete_effective_time() -> None:
    with pytest.raises(ValueError, match="effective_precision requires effective_at"):
        ActivityDraftSeed(
            activity_id="txn-1",
            timestamp=datetime(2025, 1, 1, tzinfo=UTC),
            leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
            effective_precision=TemporalPrecision.DATE,
        )


def test_economic_activity_draft_preserves_explicit_leg_policy() -> None:
    draft = EconomicActivityDraft(
        activity_id="txn-1",
        source="fixture",
        adapter_id="fixture",
        timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        location_id=LocationId("fixture:primary"),
        classification=classification(
            economic_kind=EconomicKind.SPOT_TRADE,
            projection_hint=ProjectionHint.TRADE,
            accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
            tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
        ),
        legs=(
            economic_leg(
                leg_id="primary_btc",
                kind=LegKind.PRIMARY,
                instrument="BTC",
                quantity=Decimal("1"),
            ),
            economic_leg(
                leg_id="primary_cad",
                kind=LegKind.PRIMARY,
                instrument="CAD",
                quantity=Decimal("-10"),
            ),
        ),
        leg_policy=TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
    )

    assert draft.leg_policy == TWO_SIDED_PRIMARY_EXCHANGE_POLICY


def test_economic_activity_draft_rejects_legs_that_exceed_declared_policy() -> None:
    with pytest.raises(
        ValueError, match="positive primary legs exceed declared leg policy"
    ):
        EconomicActivityDraft(
            activity_id="txn-1",
            source="fixture",
            adapter_id="fixture",
            timestamp=datetime(2025, 1, 1, tzinfo=UTC),
            location_id=LocationId("fixture:primary"),
            classification=classification(
                economic_kind=EconomicKind.SPOT_TRADE,
                projection_hint=ProjectionHint.TRADE,
                accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
                tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
            ),
            legs=(
                economic_leg(
                    leg_id="primary_btc",
                    kind=LegKind.PRIMARY,
                    instrument="BTC",
                    quantity=Decimal("1"),
                ),
                economic_leg(
                    leg_id="primary_eth",
                    kind=LegKind.PRIMARY,
                    instrument="ETH",
                    quantity=Decimal("2"),
                ),
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

    draft = EconomicActivityDraft(
        activity_id="txn-2",
        source="fixture",
        adapter_id="fixture",
        timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        location_id=LocationId("fixture:primary"),
        classification=classification(
            economic_kind=EconomicKind.SPOT_TRADE,
            projection_hint=ProjectionHint.TRADE,
            accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
            tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
        ),
        legs=(
            economic_leg(
                leg_id="primary_btc",
                kind=LegKind.PRIMARY,
                instrument="BTC",
                quantity=Decimal("1"),
            ),
            economic_leg(
                leg_id="primary_eth",
                kind=LegKind.PRIMARY,
                instrument="ETH",
                quantity=Decimal("2"),
            ),
            economic_leg(
                leg_id="fee_cad",
                kind=LegKind.CHARGE,
                instrument="CAD",
                quantity=Decimal("-10"),
                attributed_to_leg_id="primary_btc",
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

    assert draft.leg_policy.limit_for(LegKind.PRIMARY) == LegShapeLimit(
        kind=LegKind.PRIMARY,
        max_count=2,
        max_positive_count=2,
        max_negative_count=0,
    )


def test_economic_activity_draft_rejects_legs_that_fall_below_declared_policy() -> None:
    with pytest.raises(ValueError, match="primary legs fall below declared leg policy"):
        EconomicActivityDraft(
            activity_id="txn-3",
            source="fixture",
            adapter_id="fixture",
            timestamp=datetime(2025, 1, 1, tzinfo=UTC),
            location_id=LocationId("fixture:primary"),
            classification=classification(
                economic_kind=EconomicKind.SPOT_TRADE,
                projection_hint=ProjectionHint.TRADE,
                accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
                tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
            ),
            legs=(
                economic_leg(
                    leg_id="fee_cad",
                    kind=LegKind.CHARGE,
                    instrument="CAD",
                    quantity=Decimal("-10"),
                    attributed_to_leg_id="primary_btc",
                ),
            ),
            leg_policy=FactLegPolicy(
                limits=(
                    LegShapeLimit(
                        kind=LegKind.PRIMARY,
                        min_count=2,
                        max_count=2,
                        min_positive_count=1,
                        max_positive_count=1,
                        min_negative_count=1,
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


def test_economic_activity_draft_requires_utc_timestamp() -> None:
    with pytest.raises(
        ValueError, match="economic activity draft timestamp must be timezone-aware UTC"
    ):
        EconomicActivityDraft(
            activity_id="txn-utc",
            source="fixture",
            adapter_id="fixture",
            timestamp=datetime.fromisoformat("2025-01-01T00:00:00-06:00"),
            location_id=LocationId("fixture:primary"),
            classification=classification(
                economic_kind=EconomicKind.SPOT_TRADE,
                projection_hint=ProjectionHint.TRADE,
                accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
                tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
            ),
            legs=(
                economic_leg(
                    leg_id="primary_btc",
                    kind=LegKind.PRIMARY,
                    instrument="BTC",
                    quantity=Decimal("1"),
                ),
                economic_leg(
                    leg_id="primary_cad",
                    kind=LegKind.PRIMARY,
                    instrument="CAD",
                    quantity=Decimal("-10"),
                ),
            ),
            leg_policy=TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
        )


def test_economic_activity_draft_rejects_invalid_leg_metadata() -> None:
    with pytest.raises(ValueError, match="fact leg_id must be lowercase snake_case"):
        economic_leg(
            leg_id="PrimaryBTC",
            kind=LegKind.PRIMARY,
            instrument="BTC",
            quantity=Decimal("1"),
        )

    with pytest.raises(
        ValueError, match="fact leg attributed_to_leg_id must be lowercase snake_case"
    ):
        economic_leg(
            leg_id="fee_cad",
            kind=LegKind.CHARGE,
            instrument="CAD",
            quantity=Decimal("-1"),
            attributed_to_leg_id="PrimaryCad",
        )


def test_economic_activity_draft_allows_date_precision_effective_time() -> None:
    draft = EconomicActivityDraft(
        activity_id="txn-effective",
        source="fixture",
        adapter_id="fixture",
        timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        effective_at=datetime(2025, 1, 2, tzinfo=UTC),
        effective_precision=TemporalPrecision.DATE,
        location_id=LocationId("fixture:primary"),
        classification=classification(
            economic_kind=EconomicKind.CHAIN_TRANSFER_IN,
            projection_hint=ProjectionHint.DEPOSIT,
            accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
            tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
        ),
        legs=(
            economic_leg(
                leg_id="primary_btc",
                kind=LegKind.PRIMARY,
                instrument="BTC",
                quantity=Decimal("1"),
            ),
        ),
        leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
    )

    assert draft.effective_precision is TemporalPrecision.DATE
