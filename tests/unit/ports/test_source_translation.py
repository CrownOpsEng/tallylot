from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import cast

import pytest

from tallylot.domain.transactions import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
    EconomicKind,
    FactDirection,
    FactLegPolicy,
    JournalIntent,
    LegKind,
    LegShapeLimit,
    ProjectionType,
    TaxTreatmentCode,
)
from tallylot.ports.source_translation import (
    ActivityDraftSeed,
    DraftDirection,
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


def test_economic_activity_draft_preserves_explicit_leg_policy() -> None:
    draft = EconomicActivityDraft(
        activity_id="txn-1",
        source="fixture",
        adapter_id="fixture",
        timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        account="Primary",
        wallet="Primary",
        classification=classification(
            economic_kind=EconomicKind.SPOT_TRADE,
            projection_type=ProjectionType.TRADE,
            journal_intent=JournalIntent.ASSET_EXCHANGE,
            tax_treatment_code=TaxTreatmentCode.CAPITAL_EXCHANGE,
        ),
        legs=(
            economic_leg(direction="in", kind=LegKind.PRIMARY, asset="BTC", amount=Decimal("1")),
            economic_leg(direction="out", kind=LegKind.PRIMARY, asset="CAD", amount=Decimal("10")),
        ),
        leg_policy=TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
    )

    assert draft.leg_policy == TWO_SIDED_PRIMARY_EXCHANGE_POLICY


def test_economic_activity_draft_rejects_legs_that_exceed_declared_policy() -> None:
    with pytest.raises(ValueError, match="inbound primary legs exceed declared leg policy"):
        EconomicActivityDraft(
            activity_id="txn-1",
            source="fixture",
            adapter_id="fixture",
            timestamp=datetime(2025, 1, 1, tzinfo=UTC),
            account="Primary",
            wallet="Primary",
            classification=classification(
                economic_kind=EconomicKind.SPOT_TRADE,
                projection_type=ProjectionType.TRADE,
                journal_intent=JournalIntent.ASSET_EXCHANGE,
                tax_treatment_code=TaxTreatmentCode.CAPITAL_EXCHANGE,
            ),
            legs=(
                economic_leg(direction="in", kind=LegKind.PRIMARY, asset="BTC", amount=Decimal("1")),
                economic_leg(direction="in", kind=LegKind.PRIMARY, asset="ETH", amount=Decimal("2")),
            ),
            leg_policy=FactLegPolicy(
                limits=(LegShapeLimit(kind=LegKind.PRIMARY, max_count=2, max_in_count=1, max_out_count=1),)
            ),
        )

    draft = EconomicActivityDraft(
        activity_id="txn-2",
        source="fixture",
        adapter_id="fixture",
        timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        account="Primary",
        wallet="Primary",
        classification=classification(
            economic_kind=EconomicKind.SPOT_TRADE,
            projection_type=ProjectionType.TRADE,
            journal_intent=JournalIntent.ASSET_EXCHANGE,
            tax_treatment_code=TaxTreatmentCode.CAPITAL_EXCHANGE,
        ),
        legs=(
            economic_leg(direction="in", kind=LegKind.PRIMARY, asset="BTC", amount=Decimal("1")),
            economic_leg(direction="in", kind=LegKind.PRIMARY, asset="ETH", amount=Decimal("2")),
            economic_leg(direction="out", kind=LegKind.CHARGE, asset="CAD", amount=Decimal("10")),
        ),
        leg_policy=FactLegPolicy(
            limits=(
                LegShapeLimit(kind=LegKind.PRIMARY, max_count=2, max_in_count=2, max_out_count=0),
                LegShapeLimit(kind=LegKind.CHARGE, max_count=1, max_in_count=0, max_out_count=1),
            )
        ),
    )

    assert draft.leg_policy.limit_for(LegKind.PRIMARY) == LegShapeLimit(
        kind=LegKind.PRIMARY,
        max_count=2,
        max_in_count=2,
        max_out_count=0,
    )


def test_economic_activity_draft_rejects_invalid_direction_metadata() -> None:
    with pytest.raises(ValueError, match="unsupported fact leg direction: buy"):
        economic_leg(
            direction=cast(DraftDirection, "buy"),
            kind=LegKind.PRIMARY,
            asset="BTC",
            amount=Decimal("1"),
        )

    with pytest.raises(ValueError, match="unsupported fact leg attributed_to_direction: side"):
        economic_leg(
            direction="out",
            kind=LegKind.CHARGE,
            asset="CAD",
            amount=Decimal("1"),
            attributed_to_direction=cast(FactDirection, "side"),
        )
