from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.adapters.support import FileTranslationContext, FileTranslationRule, translate_file_families
from tallylot.adapters.support.drafts import (
    EconomicActivityDraft,
    classification,
    compile_activity_draft,
    economic_leg,
    transaction_fact_from_draft,
    translation_batch_from_drafts,
)
from tallylot.adapters.support.wallets import normalized_identifier, wallet_identifier_kind
from tallylot.domain.issues import IssueRecord
from tallylot.domain.transactions import EconomicKind, FactLegPolicy, JournalIntent, ProjectionType, TaxTreatmentCode
from tests.support.services import build_source_profile


def test_draft_compiler_preserves_internal_fields() -> None:
    event = compile_activity_draft(
        EconomicActivityDraft(
            activity_id="txn-1",
            source="fixture",
            adapter_id="fixture_adapter",
            account="Primary",
            wallet="Primary",
            timestamp=datetime(2023, 8, 6, 10, 0, 0, tzinfo=UTC),
            classification=classification(
                economic_kind=EconomicKind.ASSET_DEPOSIT,
                projection_type=ProjectionType.DEPOSIT,
                journal_intent=JournalIntent.FUNDING_INFLOW,
                tax_treatment_code=TaxTreatmentCode.NON_TAXABLE_TRANSFER_IN,
            ),
            description="Fixture deposit",
            raw_file="fixture.csv",
            raw_row_ref="row:2",
            legs=(economic_leg(direction="in", asset="BTC", amount=Decimal("1.5")),),
        )
    )

    assert event.economic_kind == EconomicKind.ASSET_DEPOSIT
    assert event.projection_type == ProjectionType.DEPOSIT
    assert event.journal_intent == JournalIntent.FUNDING_INFLOW
    assert event.tax_treatment_code == TaxTreatmentCode.NON_TAXABLE_TRANSFER_IN
    assert event.description == "Fixture deposit"
    assert str(event.legs[0].asset) == "BTC"


def test_wallet_identifier_helpers_normalize_evm_and_classify_near_accounts() -> None:
    assert normalized_identifier("evm_address", "0xABCDEF") == "0xabcdef"
    assert wallet_identifier_kind("example.near") == "near_account"


def test_transaction_fact_from_draft_preserves_multi_leg_shape() -> None:
    fact = transaction_fact_from_draft(
        EconomicActivityDraft(
            activity_id="txn-1",
            source="fixture",
            adapter_id="fixture_adapter",
            account="Primary",
            wallet="Primary",
            timestamp=datetime(2023, 8, 6, 10, 0, 0, tzinfo=UTC),
            classification=classification(
                economic_kind=EconomicKind.SPOT_TRADE,
                projection_type=ProjectionType.TRADE,
                journal_intent=JournalIntent.ASSET_EXCHANGE,
                tax_treatment_code=TaxTreatmentCode.CAPITAL_EXCHANGE,
            ),
            legs=(
                economic_leg(direction="in", asset="BTC", amount=Decimal("1.5")),
                economic_leg(direction="out", asset="CAD", amount=Decimal("10")),
            ),
        )
    )

    assert fact.economic_kind == EconomicKind.SPOT_TRADE
    assert fact.projection_type == ProjectionType.TRADE
    assert fact.journal_intent == JournalIntent.ASSET_EXCHANGE
    assert fact.tax_treatment_code == TaxTreatmentCode.CAPITAL_EXCHANGE
    assert fact.leg_policy == FactLegPolicy()
    assert len(fact.legs) == 2
    assert fact.legs[0].asset == "BTC"
    assert fact.legs[1].asset == "CAD"
    assert fact.legs[0].direction == "in"
    assert fact.legs[1].direction == "out"


def test_translation_batch_from_drafts_compiles_transactions_and_preserves_side_channels() -> None:
    result = translation_batch_from_drafts(
        (
            EconomicActivityDraft(
                activity_id="txn-1",
                source="fixture",
                adapter_id="fixture_adapter",
                account="Primary",
                wallet="Primary",
                timestamp=datetime(2023, 8, 6, 10, 0, 0, tzinfo=UTC),
                classification=classification(
                    economic_kind=EconomicKind.ASSET_DEPOSIT,
                    projection_type=ProjectionType.DEPOSIT,
                    journal_intent=JournalIntent.FUNDING_INFLOW,
                    tax_treatment_code=TaxTreatmentCode.NON_TAXABLE_TRANSFER_IN,
                ),
                raw_file="fixture.csv",
                raw_row_ref="row:2",
                legs=(economic_leg(direction="in", asset="BTC", amount=Decimal("1.5")),),
            ),
        ),
        issues=(),
        reviews=(),
        wallet_inventory=(),
    )

    assert len(result.facts) == 1
    assert result.facts[0].economic_kind == EconomicKind.ASSET_DEPOSIT
    assert result.facts[0].projection_type == ProjectionType.DEPOSIT
    assert result.facts[0].journal_intent == JournalIntent.FUNDING_INFLOW
    assert result.facts[0].tax_treatment_code == TaxTreatmentCode.NON_TAXABLE_TRANSFER_IN
    assert result.facts[0].leg_policy == FactLegPolicy()
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
