from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from tallylot.adapters.support.drafts import compile_activity_drafts_with_feedback
from tallylot.domain.instruments import InstrumentKind
from tallylot.domain.transactions import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    AccountingIntentHint,
    EconomicKind,
    LegKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.domain.types import LocationId
from tallylot.ports.source_translation import (
    EconomicActivityDraft,
    classification,
    economic_leg,
    symbol_claim,
)


def test_compile_activity_drafts_with_feedback_emits_fact_for_resolved_claims() -> None:
    result = compile_activity_drafts_with_feedback(
        (
            EconomicActivityDraft(
                activity_id="txn-1",
                source="fixture",
                adapter_id="fixture",
                timestamp=datetime(2025, 1, 1, tzinfo=UTC),
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
                        instrument=symbol_claim(
                            "BTC", venue="coinbase", kind_hint=InstrumentKind.CRYPTO
                        ),
                        quantity=Decimal("1"),
                    ),
                ),
                leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
            ),
        )
    )

    assert len(result.facts) == 1
    assert not result.issues
    assert not result.reviews
    assert str(result.facts[0].legs[0].instrument_id) == "symbol:BTC@coinbase"


def test_compile_activity_drafts_with_feedback_blocks_ambiguous_instrument_claims() -> (
    None
):
    result = compile_activity_drafts_with_feedback(
        (
            EconomicActivityDraft(
                activity_id="txn-2",
                source="fixture",
                adapter_id="fixture",
                timestamp=datetime(2025, 1, 1, tzinfo=UTC),
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
                        instrument=(
                            symbol_claim("BTC", kind_hint=InstrumentKind.CRYPTO),
                            symbol_claim(
                                "BTC", venue="coinbase", kind_hint=InstrumentKind.CRYPTO
                            ),
                        ),
                        quantity=Decimal("1"),
                    ),
                ),
                leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
            ),
        )
    )

    assert not result.facts
    assert [issue.kind for issue in result.issues] == ["instrument_identity_blocked"]
    assert [review.kind for review in result.reviews] == ["instrument_identity_review"]
    assert result.issues[0].issue_id == "txn-2:primary_btc:instrument_identity_blocked"
    assert result.reviews[0].review_id == "txn-2:primary_btc:instrument_identity_review"
