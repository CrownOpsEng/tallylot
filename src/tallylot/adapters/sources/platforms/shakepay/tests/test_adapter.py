from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.platforms.shakepay.translation import translate_row
from tallylot.adapters.support import CsvRowContext
from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.domain.issues import IssueRecord
from tallylot.domain.transactions import AccountingIntentHint, EconomicKind, ProjectionHint, TaxTreatmentHint
from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter


def test_shakepay_adapter_normalizes_fixture_rows() -> None:
    raw_dir = fixture_raw_dir("shakepay", "cash_crypto_mix")

    profile, adapter = profile_and_adapter("Shakepay", raw_dir)
    result = adapter.translate(profile, raw_dir)
    facts = compile_activity_drafts(result.drafts)

    assert str(profile.adapter_id) == "shakepay"
    assert {event.economic_kind for event in facts} == {
        EconomicKind.FIAT_DEPOSIT,
        EconomicKind.CASH_EXPENSE,
        EconomicKind.CASH_WITHDRAWAL,
        EconomicKind.ASSET_WITHDRAWAL,
        EconomicKind.PLATFORM_REWARD,
        EconomicKind.SPOT_TRADE,
    }
    assert {event.projection_hint for event in facts} == {
        ProjectionHint.DEPOSIT,
        ProjectionHint.EXPENSE_NON_TAXABLE,
        ProjectionHint.REWARD_BONUS,
        ProjectionHint.TRADE,
        ProjectionHint.WITHDRAWAL,
    }
    assert {event.accounting_intent_hint for event in facts} == {
        AccountingIntentHint.FUNDING_INFLOW,
        AccountingIntentHint.EXPENSE_RECOGNITION,
        AccountingIntentHint.FUNDING_OUTFLOW,
        AccountingIntentHint.INCOME_RECOGNITION,
        AccountingIntentHint.ASSET_EXCHANGE,
    }
    assert {event.tax_treatment_hint for event in facts} == {
        TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
        TaxTreatmentHint.NON_TAXABLE_EXPENSE,
        TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
        TaxTreatmentHint.ORDINARY_INCOME,
        TaxTreatmentHint.CAPITAL_EXCHANGE,
    }
    trade_event = next(event for event in facts if event.projection_hint == ProjectionHint.TRADE)
    primary_legs = tuple(leg for leg in trade_event.legs if leg.kind.value == "primary")
    assert primary_legs[0].quantity > 0
    assert primary_legs[1].quantity < 0
    assert any(event.description == "shakingsats" for event in facts)
    assert result.balance_evidence == ()
    assert result.issues == ()


def test_shakepay_adapter_ignores_manifest_csv(tmp_path: Path) -> None:
    raw_dir = fixture_raw_dir("shakepay", "cash_crypto_mix")
    for source_path in raw_dir.iterdir():
        target_path = tmp_path / source_path.name
        target_path.write_bytes(source_path.read_bytes())
    (tmp_path / "manifest.csv").write_text(
        "filename,size_bytes\ncash_transactions_summary.csv,1\n",
        encoding="utf-8",
    )

    profile, adapter = profile_and_adapter("Shakepay", tmp_path)
    result = adapter.translate(profile, tmp_path)
    facts = compile_activity_drafts(result.drafts)

    assert len(facts) == 6
    assert result.issues == ()


def test_shakepay_invalid_timestamp_surfaces_issue() -> None:
    profile, _ = profile_and_adapter("Shakepay", fixture_raw_dir("shakepay", "cash_crypto_mix"))

    parsed = translate_row(
        profile,
        CsvRowContext(
            path=Path("cash_transactions_summary.csv"),
            row_index=2,
            row={
                "Date": "",
                "Type": "E-Transfer",
                "Description": "fixture",
                "Debit": "",
                "Credit": "10.00",
            },
        ),
    )

    assert parsed is not None
    assert isinstance(parsed, IssueRecord)
    assert parsed.kind == "unsupported_row"
    assert parsed.raw_row_ref == "row:2"
