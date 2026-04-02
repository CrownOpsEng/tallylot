from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.platforms.crypto_com.adapter import CryptoComAdapter
from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.domain.transactions import EconomicKind, JournalIntent, ProjectionType, TaxTreatmentCode
from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter
from tests.support.services import build_source_profile


def test_crypto_com_adapter_uses_transaction_kinds_without_filename_dependency() -> None:
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
    assert [event.projection_type for event in facts] == [
        ProjectionType.DEPOSIT,
        ProjectionType.TRADE,
        ProjectionType.WITHDRAWAL,
    ]
    assert [event.journal_intent for event in facts] == [
        JournalIntent.FUNDING_INFLOW,
        JournalIntent.ASSET_EXCHANGE,
        JournalIntent.FUNDING_OUTFLOW,
    ]
    assert [event.tax_treatment_code for event in facts] == [
        TaxTreatmentCode.NON_TAXABLE_TRANSFER_IN,
        TaxTreatmentCode.CAPITAL_EXCHANGE,
        TaxTreatmentCode.NON_TAXABLE_TRANSFER_OUT,
    ]
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

    result = CryptoComAdapter().translate(
        build_source_profile(adapter_id="crypto_com", raw_dir=str(raw_dir), source="Crypto.com"),
        raw_dir,
    )

    assert [event.projection_type for event in compile_activity_drafts(result.drafts)] == [ProjectionType.DEPOSIT]
    assert not result.issues
