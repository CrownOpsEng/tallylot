from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.domain.transactions import (
    AccountingIntentHint,
    EconomicKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.ports.intake_routing import IntakeFileFacts
from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter


def test_crypto_com_adapter_uses_transaction_kinds_without_filename_dependency() -> (
    None
):
    raw_dir = fixture_raw_dir("crypto_com", "transaction_kinds")

    profile, adapter = profile_and_adapter("Future Card", raw_dir)
    result = adapter.translate(profile, raw_dir)
    facts = compile_activity_drafts(result.drafts)

    assert str(profile.adapter_id) == "crypto_com"
    assert [event.economic_kind for event in facts] == [
        EconomicKind.FIAT_DEPOSIT,
        EconomicKind.SPOT_TRADE,
        EconomicKind.ASSET_WITHDRAWAL,
    ]
    assert [event.projection_hint for event in facts] == [
        ProjectionHint.DEPOSIT,
        ProjectionHint.TRADE,
        ProjectionHint.WITHDRAWAL,
    ]
    assert [event.accounting_intent_hint for event in facts] == [
        AccountingIntentHint.FUNDING_INFLOW,
        AccountingIntentHint.ASSET_EXCHANGE,
        AccountingIntentHint.FUNDING_OUTFLOW,
    ]
    assert [event.tax_treatment_hint for event in facts] == [
        TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
        TaxTreatmentHint.CAPITAL_EXCHANGE,
        TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
    ]
    assert facts[0].legs[0].quantity == Decimal("500")
    assert facts[1].legs[0].quantity > 0
    assert facts[1].legs[1].quantity < 0
    assert facts[2].legs[0].quantity < 0
    assert {event.raw_file for event in facts} == {"records-a.csv", "records-b.csv"}
    assert not result.issues


def test_crypto_com_adapter_ignores_unrecognized_csv_files(tmp_path: Path) -> None:
    raw_dir = tmp_path
    (raw_dir / "records-a.csv").write_text(
        "Timestamp (UTC),Transaction Description,Currency,Amount,To Currency,To Amount,Transaction Kind\n"
        "2023-09-01 10:00:00,Deposit,CAD,100,,,viban_deposit\n",
        encoding="utf-8",
    )
    (raw_dir / "other.csv").write_text(
        "not,a,crypto,com,file\ntotally,unrelated,row,with,bad-date\n",
        encoding="utf-8",
    )

    profile, adapter = profile_and_adapter("Future Card", raw_dir)
    result = adapter.translate(profile, raw_dir)

    assert [
        event.projection_hint for event in compile_activity_drafts(result.drafts)
    ] == [ProjectionHint.DEPOSIT]
    assert not result.issues


def test_crypto_com_adapter_matches_transaction_headers_for_intake() -> None:
    header = (
        "Timestamp (UTC)",
        "Transaction Description",
        "Currency",
        "Amount",
        "To Currency",
        "To Amount",
        "Native Currency",
        "Native Amount",
        "Native Amount (in USD)",
        "Transaction Kind",
        "Transaction Hash",
    )

    _, adapter = profile_and_adapter(
        "Future Card", fixture_raw_dir("crypto_com", "transaction_kinds")
    )

    match_score = adapter.match_intake(
        "records-a.csv",
        IntakeFileFacts(header=header),
    )
    assert match_score == 100


def test_crypto_com_adapter_surfaces_positive_purchase_rows_as_issues(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path
    payload = (
        "Timestamp (UTC),Transaction Description,Currency,Amount,To Currency,"
        "To Amount,Native Currency,Native Amount,Native Amount (in USD),"
        "Transaction Kind,Transaction Hash\n"
        "2023-09-01 10:00:00,Crypto buy,CAD,250,BTC,0.005,CAD,250,250,"
        "viban_purchase,trade-1\n"
    )
    (raw_dir / "records-a.csv").write_text(payload, encoding="utf-8")

    profile, adapter = profile_and_adapter("Future Card", raw_dir)
    result = adapter.translate(profile, raw_dir)

    assert [issue.kind for issue in result.issues] == ["unsupported_row"]
    assert "positive CAD amounts" in result.issues[0].message
    assert not result.drafts
