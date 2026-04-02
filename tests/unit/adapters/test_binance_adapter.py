from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.adapters.sources.binance.adapter import _normalize_transaction_rows, _parse_offset_timestamp
from tests.support.services import build_source_profile


def test_parse_offset_timestamp_applies_binance_filename_offset() -> None:
    parsed = _parse_offset_timestamp(
        "23-03-23 04:06:00",
        "Binance-Spot-Trade-History-202603230406(UTC--6)_abcd.csv",
    )

    assert parsed.strftime("%Y-%m-%d %H:%M:%S") == "2023-03-23 10:06:00"


def test_binance_transaction_history_normalizes_small_assets_and_surfaces_ambiguous_groups(tmp_path: Path) -> None:
    path = tmp_path / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv"
    path.write_text(
        "User ID,Time,Account,Operation,Coin,Change,Remark\n"
        "1,23-03-23 04:00:00,Spot,Small Assets Exchange BNB,ADA,-10.0,Dust conversion\n"
        "1,23-03-23 04:00:00,Spot,Small Assets Exchange BNB,BNB,0.1,Dust conversion\n"
        "1,23-03-23 05:00:00,Spot,Binance Convert,BTC,-0.5,Convert out\n",
        encoding="utf-8",
    )

    events, issues = _normalize_transaction_rows(
        build_source_profile(adapter_id="binance"),
        path,
    )

    assert len(events) == 1
    assert events[0].event_kind == "Trade"
    assert str(events[0].asset_in) == "BNB"
    assert str(events[0].asset_out) == "ADA"
    assert len(issues) == 1
    assert issues[0].kind == "ambiguous_group"
