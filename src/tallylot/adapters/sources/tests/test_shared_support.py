from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.adapters.support import FileTranslationContext, FileTranslationRule, translate_file_families
from tallylot.adapters.support.drafts import (
    EconomicActivityDraft,
    classification,
    compile_activity_draft,
    compile_activity_drafts,
    economic_leg,
    transaction_fact_from_draft,
    translation_batch_from_drafts,
)
from tallylot.adapters.support.locations import location_identifier_kind, normalized_identifier
from tallylot.domain.issues import IssueRecord
from tallylot.domain.transactions import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
    AccountingIntentHint,
    EconomicKind,
    LegKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.domain.types import LocationId
from tests.support.services import build_source_profile


def test_draft_compiler_preserves_internal_fields() -> None:
    event = compile_activity_draft(
        EconomicActivityDraft(
            activity_id="txn-1",
            source="fixture",
            adapter_id="fixture_adapter",
            location_id=LocationId("fixture:primary"),
            timestamp=datetime(2023, 8, 6, 10, 0, 0, tzinfo=UTC),
            classification=classification(
                economic_kind=EconomicKind.ASSET_DEPOSIT,
                projection_hint=ProjectionHint.DEPOSIT,
                accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
                tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
            ),
            description="Fixture deposit",
            raw_file="fixture.csv",
            raw_row_ref="row:2",
            legs=(economic_leg(direction="in", kind=LegKind.PRIMARY, asset="BTC", amount=Decimal("1.5")),),
            leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
        )
    )

    assert event.economic_kind == EconomicKind.ASSET_DEPOSIT
    assert event.projection_hint == ProjectionHint.DEPOSIT
    assert event.accounting_intent_hint == AccountingIntentHint.FUNDING_INFLOW
    assert event.tax_treatment_hint == TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN
    assert event.description == "Fixture deposit"
    assert str(event.legs[0].asset) == "BTC"


def test_location_identifier_helpers_normalize_evm_and_classify_near_accounts() -> None:
    assert normalized_identifier("evm_address", "0xABCDEF") == "0xabcdef"
    assert location_identifier_kind("example.near") == "near_account"


def test_transaction_fact_from_draft_preserves_multi_leg_shape() -> None:
    fact = transaction_fact_from_draft(
        EconomicActivityDraft(
            activity_id="txn-1",
            source="fixture",
            adapter_id="fixture_adapter",
            location_id=LocationId("fixture:primary"),
            timestamp=datetime(2023, 8, 6, 10, 0, 0, tzinfo=UTC),
            classification=classification(
                economic_kind=EconomicKind.SPOT_TRADE,
                projection_hint=ProjectionHint.TRADE,
                accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
                tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
            ),
            legs=(
                economic_leg(direction="in", kind=LegKind.PRIMARY, asset="BTC", amount=Decimal("1.5")),
                economic_leg(direction="out", kind=LegKind.PRIMARY, asset="CAD", amount=Decimal("10")),
            ),
            leg_policy=TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
        )
    )

    assert fact.economic_kind == EconomicKind.SPOT_TRADE
    assert fact.projection_hint == ProjectionHint.TRADE
    assert fact.accounting_intent_hint == AccountingIntentHint.ASSET_EXCHANGE
    assert fact.tax_treatment_hint == TaxTreatmentHint.CAPITAL_EXCHANGE
    assert fact.leg_policy == TWO_SIDED_PRIMARY_EXCHANGE_POLICY
    assert len(fact.legs) == 2
    assert str(fact.legs[0].asset) == "BTC"
    assert str(fact.legs[1].asset) == "CAD"
    assert fact.legs[0].direction == "in"
    assert fact.legs[1].direction == "out"


def test_translation_batch_from_drafts_compiles_transactions_and_preserves_side_channels() -> None:
    result = translation_batch_from_drafts(
        (
            EconomicActivityDraft(
                activity_id="txn-1",
                source="fixture",
                adapter_id="fixture_adapter",
                location_id=LocationId("fixture:primary"),
                timestamp=datetime(2023, 8, 6, 10, 0, 0, tzinfo=UTC),
                classification=classification(
                    economic_kind=EconomicKind.ASSET_DEPOSIT,
                    projection_hint=ProjectionHint.DEPOSIT,
                    accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
                    tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
                ),
                raw_file="fixture.csv",
                raw_row_ref="row:2",
                legs=(economic_leg(direction="in", kind=LegKind.PRIMARY, asset="BTC", amount=Decimal("1.5")),),
                leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
            ),
        ),
        issues=(),
        reviews=(),
        location_inventory=(),
    )

    facts = compile_activity_drafts(result.drafts)
    assert len(facts) == 1
    assert facts[0].economic_kind == EconomicKind.ASSET_DEPOSIT
    assert facts[0].projection_hint == ProjectionHint.DEPOSIT
    assert facts[0].accounting_intent_hint == AccountingIntentHint.FUNDING_INFLOW
    assert facts[0].tax_treatment_hint == TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN
    assert facts[0].leg_policy == SINGLE_PRIMARY_ACTIVITY_POLICY
    assert not result.issues


def test_translate_file_families_surfaces_ambiguous_and_unmatched_files(tmp_path: Path) -> None:
    (tmp_path / "alpha.csv").write_text("x\n1\n", encoding="utf-8")
    (tmp_path / "beta.csv").write_text("x\n1\n", encoding="utf-8")

    def translate(
        context: FileTranslationContext,
    ) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
        del context
        return (), ()

    alpha_one = FileTranslationRule(
        family="alpha_one",
        matches_path=lambda path: path.name == "alpha.csv",
        translate=translate,
    )
    alpha_two = FileTranslationRule(
        family="alpha_two",
        matches_path=lambda path: path.name == "alpha.csv",
        translate=translate,
    )

    result = translate_file_families(
        tmp_path,
        profile=build_source_profile(adapter_id="fixture_adapter", raw_dir=str(tmp_path)),
        rules=(alpha_one, alpha_two),
    )

    assert result.unmatched_paths == ("beta.csv",)
    assert {issue.kind for issue in result.issues} == {"ambiguous_file_match", "unsupported_file"}
