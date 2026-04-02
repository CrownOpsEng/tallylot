from __future__ import annotations

from tallylot.adapters.support.drafts import compile_activity_drafts
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
    assert any(event.description == "shakingsats" for event in facts)
    assert result.balance_evidence == ()
    assert result.issues == ()
