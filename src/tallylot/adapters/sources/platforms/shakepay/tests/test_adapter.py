from __future__ import annotations

from tallylot.domain.transactions import EconomicKind, JournalIntent, ProjectionType, TaxTreatmentCode
from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter


def test_shakepay_adapter_normalizes_fixture_rows() -> None:
    raw_dir = fixture_raw_dir("shakepay", "cash_crypto_mix")

    profile, adapter = profile_and_adapter("Shakepay", raw_dir)
    result = adapter.translate(profile, raw_dir)

    assert str(profile.adapter_id) == "shakepay"
    assert {event.economic_kind for event in result.facts} == {
        EconomicKind.FIAT_DEPOSIT,
        EconomicKind.CASH_EXPENSE,
        EconomicKind.CASH_WITHDRAWAL,
        EconomicKind.ASSET_WITHDRAWAL,
        EconomicKind.PLATFORM_REWARD,
        EconomicKind.SPOT_TRADE,
    }
    assert {event.projection_type for event in result.facts} == {
        ProjectionType.DEPOSIT,
        ProjectionType.EXPENSE_NON_TAXABLE,
        ProjectionType.REWARD_BONUS,
        ProjectionType.TRADE,
        ProjectionType.WITHDRAWAL,
    }
    assert {event.journal_intent for event in result.facts} == {
        JournalIntent.FUNDING_INFLOW,
        JournalIntent.EXPENSE_RECOGNITION,
        JournalIntent.FUNDING_OUTFLOW,
        JournalIntent.INCOME_RECOGNITION,
        JournalIntent.ASSET_EXCHANGE,
    }
    assert {event.tax_treatment_code for event in result.facts} == {
        TaxTreatmentCode.NON_TAXABLE_TRANSFER_IN,
        TaxTreatmentCode.NON_TAXABLE_EXPENSE,
        TaxTreatmentCode.NON_TAXABLE_TRANSFER_OUT,
        TaxTreatmentCode.ORDINARY_INCOME,
        TaxTreatmentCode.CAPITAL_EXCHANGE,
    }
    assert any(event.description == "shakingsats" for event in result.facts)
    assert result.balance_evidence == ()
    assert result.issues == ()
