from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.adapters.sources.platforms.wealthsimple.adapter import WealthsimpleAdapter
from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter
from tests.support.services import build_source_profile


def test_wealthsimple_fixture_exercises_supported_and_unsupported_rows() -> None:
    raw_dir = fixture_raw_dir("wealthsimple", "mixed_activity_review")

    profile, adapter = profile_and_adapter("WealthSimple", raw_dir)
    result = adapter.translate(profile, raw_dir)

    assert str(profile.adapter_id) == "wealthsimple"
    assert len(result.facts) == 1
    assert result.facts[0].category == "trade"
    assert str(result.facts[0].timestamp) == "2023-09-22 00:00:00"
    assert len(result.issues) == 1
    assert result.issues[0].kind == "unsupported_row"
    assert "Staking/REWARD" in result.issues[0].message


def test_wealthsimple_adapter_uses_broker_activity_family_without_filename_dependency() -> None:
    raw_dir = fixture_raw_dir("wealthsimple", "broker_trade")

    profile, adapter = profile_and_adapter("Future Broker", raw_dir)
    result = adapter.translate(profile, raw_dir)

    assert str(profile.adapter_id) == "wealthsimple"
    assert len(result.facts) == 1
    assert result.facts[0].raw_file == "broker-export.csv"
    assert not result.issues


def test_wealthsimple_adapter_ignores_unrecognized_csv_files(tmp_path: Path) -> None:
    raw_dir = tmp_path
    (raw_dir / "broker-export.csv").write_text(
        ",".join(
            (
                "transaction_date",
                "settlement_date",
                "account_id",
                "account_type",
                "activity_type",
                "activity_sub_type",
                "direction",
                "symbol",
                "name",
                "currency",
                "quantity",
                "unit_price",
                "commission",
                "net_cash_amount",
            )
        )
        + "\n2023-09-20,2023-09-22,acct-1,Crypto,trade,BUY,,BTC,Bitcoin,CAD,0.1,30000,10,-3000\n",
        encoding="utf-8",
    )
    (raw_dir / "other.csv").write_text("a,b,c\nbad,row,data\n", encoding="utf-8")

    result = WealthsimpleAdapter().translate(
        build_source_profile(adapter_id="wealthsimple", raw_dir=str(raw_dir), source="Wealthsimple"),
        raw_dir,
    )

    assert len(result.facts) == 1
    assert not result.issues
