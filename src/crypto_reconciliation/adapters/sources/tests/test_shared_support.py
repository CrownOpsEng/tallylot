from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.adapters.support import FileTranslationContext, FileTranslationRule, translate_file_families
from crypto_reconciliation.adapters.support.drafts import (
    EconomicActivityDraft,
    classification,
    compile_activity_draft,
    economic_leg,
    normalization_result_from_drafts,
)
from crypto_reconciliation.adapters.support.wallets import normalized_identifier, wallet_identifier_kind
from crypto_reconciliation.domain.models import IssueRecord
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
                normalized_category="deposit",
                economic_kind="asset_deposit",
                projection_type="Deposit",
                journal_intent="funding_inflow",
                tax_treatment_code="non_taxable_transfer_in",
            ),
            description="Fixture deposit",
            raw_file="fixture.csv",
            raw_row_ref="row:2",
            legs=(economic_leg(direction="in", asset="BTC", amount=Decimal("1.5")),),
        )
    )

    assert event.category == "deposit"
    assert event.description == "Fixture deposit"
    assert str(event.asset_in) == "BTC"


def test_wallet_identifier_helpers_normalize_evm_and_classify_near_accounts() -> None:
    assert normalized_identifier("evm_address", "0xABCDEF") == "0xabcdef"
    assert wallet_identifier_kind("example.near") == "near_account"


def test_normalization_result_from_drafts_compiles_transactions_and_preserves_side_channels() -> None:
    result = normalization_result_from_drafts(
        (
            EconomicActivityDraft(
                activity_id="txn-1",
                source="fixture",
                adapter_id="fixture_adapter",
                account="Primary",
                wallet="Primary",
                timestamp=datetime(2023, 8, 6, 10, 0, 0, tzinfo=UTC),
                classification=classification(
                    normalized_category="deposit",
                    economic_kind="asset_deposit",
                    projection_type="Deposit",
                    journal_intent="funding_inflow",
                    tax_treatment_code="non_taxable_transfer_in",
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

    assert len(result.transactions) == 1
    assert result.transactions[0].projection_type == "Deposit"
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
