from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.adapters.sources.binance.field_parsing import amount_with_asset, row_change, split_pair
from crypto_reconciliation.adapters.sources.binance.timestamps import parse_export_timestamp
from crypto_reconciliation.adapters.sources.binance.transaction_history import normalize_transaction_rows
from tests.support.services import build_source_profile


def test_binance_transaction_history_normalizes_small_assets_and_surfaces_ambiguous_groups(tmp_path: Path) -> None:
    path = tmp_path / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv"
    path.write_text(
        "User ID,Time,Account,Operation,Coin,Change,Remark\n"
        "1,23-03-23 04:00:00,Spot,Small Assets Exchange BNB,ADA,-10.0,Dust conversion\n"
        "1,23-03-23 04:00:00,Spot,Small Assets Exchange BNB,BNB,0.1,Dust conversion\n"
        "1,23-03-23 05:00:00,Spot,Binance Convert,BTC,-0.5,Convert out\n",
        encoding="utf-8",
    )

    events, issues = normalize_transaction_rows(
        build_source_profile(adapter_id="binance"),
        path,
    )

    assert len(events) == 1
    assert events[0].event_kind == "Trade"
    assert str(events[0].asset_in) == "BNB"
    assert str(events[0].asset_out) == "ADA"
    assert len(issues) == 1
    assert issues[0].kind == "ambiguous_group"


def test_binance_transaction_history_ignores_no_data_rows_and_maps_staking_rewards(tmp_path: Path) -> None:
    path = tmp_path / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv"
    path.write_text(
        "User ID,Time,Account,Operation,Coin,Change,Remark\n"
        "No data matches the criteria.\n"
        "1,23-03-23 04:00:00,Earn,ETH 2.0 Staking Rewards,ETH,0.005,Reward\n",
        encoding="utf-8",
    )

    events, issues = normalize_transaction_rows(
        build_source_profile(adapter_id="binance"),
        path,
    )

    assert len(events) == 1
    assert events[0].event_kind == "Staking"
    assert str(events[0].asset_in) == "ETH"
    assert not issues


def test_binance_historical_ignore_list_only_applies_when_profile_supplies_cutoff_hint(tmp_path: Path) -> None:
    path = tmp_path / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv"
    path.write_text(
        "User ID,Time,Account,Operation,Coin,Change,Remark\n"
        "1,23-08-05 08:34:04,Funding,Transfer Between Main and Funding Wallet,USDT,-10,\n"
        "1,23-08-05 08:34:04,Spot,Transfer Between Main and Funding Wallet,USDT,10,\n",
        encoding="utf-8",
    )
    profile_without_cutoff = build_source_profile(adapter_id="binance")
    profile_with_cutoff = build_source_profile(
        adapter_id="binance",
        normalization_hints={"project_baseline_cutoff_timestamp": "2023-08-05 08:34:04"},
    )

    without_cutoff_events, without_cutoff_issues = normalize_transaction_rows(profile_without_cutoff, path)
    with_cutoff_events, with_cutoff_issues = normalize_transaction_rows(profile_with_cutoff, path)

    assert not without_cutoff_events
    assert len(without_cutoff_issues) == 2
    assert not with_cutoff_events
    assert not with_cutoff_issues


def test_binance_transaction_history_skips_non_positive_staking_and_incomplete_dust_groups(
    tmp_path: Path,
) -> None:
    path = tmp_path / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv"
    path.write_text(
        "User ID,Time,Account,Operation,Coin,Change,Remark\n"
        "1,23-03-23 04:00:00,Earn,ETH 2.0 Staking Rewards,ETH,0,Reward\n"
        "1,23-03-23 05:00:00,Spot,Small Assets Exchange BNB,ADA,-10.0,Dust conversion\n",
        encoding="utf-8",
    )

    events, issues = normalize_transaction_rows(
        build_source_profile(adapter_id="binance"),
        path,
    )

    assert not events
    assert len(issues) == 1
    assert issues[0].kind == "unsupported_group"


def test_binance_field_parsing_helpers_cover_fallback_paths() -> None:
    assert split_pair("DOGEUSDT") == ("DOGE", "USDT")
    assert split_pair("UNKNOWN") == ("", "")
    assert amount_with_asset("0.5eth") == (Decimal("0.5"), "ETH")
    assert amount_with_asset("0.5") == (Decimal("0.5"), "")
    assert parse_export_timestamp("23-03-23 04:06:00", "Binance.csv").strftime("%Y-%m-%d %H:%M:%S") == (
        "2023-03-23 04:06:00"
    )
    assert row_change({"Change": ""}) == Decimal("0")
