from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from tallylot.application.normalization.annotations import annotation_records_from_drafts
from tallylot.domain.transactions import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    AccountingIntentHint,
    EconomicKind,
    LegKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.domain.types import LocationId
from tallylot.ports.source_translation import EconomicActivityDraft, classification, economic_leg


def test_annotation_records_preserve_draft_provenance_and_review_markers() -> None:
    records = annotation_records_from_drafts(
        (
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
                ),
                leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
                provenance_refs=("file:row:2", "statement:page:1"),
                review_markers=("normalized_negative_fee",),
            ),
        )
    )

    assert [record.to_json() for record in records] == [
        {
            "fact_id": "txn-1",
            "provenance_refs": ["file:row:2", "statement:page:1"],
            "review_markers": ["normalized_negative_fee"],
            "adapter_metadata": [],
        }
    ]
