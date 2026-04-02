from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from tallylot.domain.transactions import EconomicKind, FactLegPolicy, JournalIntent, ProjectionType, TaxTreatmentCode
from tallylot.ports.source_translation import ActivityDraftSeed, EconomicActivityDraft, classification, economic_leg


def test_activity_draft_seed_defaults_to_strict_leg_policy() -> None:
    seed = ActivityDraftSeed(
        activity_id="txn-1",
        timestamp=datetime(2025, 1, 1, tzinfo=UTC),
    )

    assert seed.leg_policy == FactLegPolicy()


def test_economic_activity_draft_defaults_to_strict_leg_policy() -> None:
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
            economic_leg(direction="in", asset="BTC", amount=Decimal("1")),
            economic_leg(direction="out", asset="CAD", amount=Decimal("10")),
        ),
    )

    assert draft.leg_policy == FactLegPolicy()


def test_economic_activity_draft_rejects_legs_that_exceed_declared_policy() -> None:
    with pytest.raises(ValueError, match="inbound legs exceed declared leg policy"):
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
                economic_leg(direction="in", asset="BTC", amount=Decimal("1")),
                economic_leg(direction="in", asset="ETH", amount=Decimal("2")),
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
            economic_leg(direction="in", asset="BTC", amount=Decimal("1")),
            economic_leg(direction="in", asset="ETH", amount=Decimal("2")),
            economic_leg(direction="out", asset="CAD", amount=Decimal("10")),
        ),
        leg_policy=FactLegPolicy(max_in_legs=2, max_out_legs=1, max_fee_legs=0),
    )

    assert draft.leg_policy.max_in_legs == 2
