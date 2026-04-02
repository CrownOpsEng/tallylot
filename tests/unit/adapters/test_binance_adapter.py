from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.adapters.sources.binance.adapter import (
    SPOT_HEADER,
    BinanceAdapter,
    _amount_with_asset,
    _is_no_data_row,
    _normalize_deposit_rows,
    _normalize_spot_rows,
    _normalize_transaction_rows,
    _normalize_withdraw_rows,
    _parse_offset_timestamp,
    _row_change,
    _split_pair,
)
from crypto_reconciliation.domain.models import FileInventoryEntry
from tests.support.services import build_source_profile


def test_parse_offset_timestamp_applies_binance_filename_offset() -> None:
    parsed = _parse_offset_timestamp(
        "23-03-23 04:06:00",
        "Binance-Spot-Trade-History-202603230406(UTC--6)_abcd.csv",
    )

    assert parsed.strftime("%Y-%m-%d %H:%M:%S") == "2023-03-23 10:06:00"


def test_binance_adapter_matches_known_headers_without_source_label(tmp_path: Path) -> None:
    adapter = BinanceAdapter()
    inventory = (
        FileInventoryEntry(
            relative_path="nested/export.csv",
            suffix=".csv",
            size_bytes=1,
            sha256="abc",
            header=SPOT_HEADER,
        ),
    )

    assert adapter.match("unknown_source", tmp_path, inventory) == 100


def test_binance_adapter_returns_zero_for_unknown_source_without_matching_headers(tmp_path: Path) -> None:
    adapter = BinanceAdapter()

    score = adapter.match(
        "unknown_source",
        tmp_path,
        (
            FileInventoryEntry(
                relative_path="notes.txt",
                suffix=".txt",
                size_bytes=1,
                sha256="abc",
            ),
        ),
    )

    assert score == 0


def test_binance_adapter_reports_timezone_validation_summary_from_inventory() -> None:
    adapter = BinanceAdapter()
    profile = build_source_profile(adapter_id="binance")
    object.__setattr__(
        profile,
        "file_inventory",
        (
            FileInventoryEntry(
                relative_path="dated.csv",
                suffix=".csv",
                size_bytes=1,
                sha256="a",
                date_field="Time",
            ),
            FileInventoryEntry(
                relative_path="undated.csv",
                suffix=".csv",
                size_bytes=1,
                sha256="b",
            ),
        ),
    )

    summary, issues = adapter.validate_profile_timezones(profile)

    assert summary == {
        "status": "passed",
        "issue_count": 0,
        "rows_with_dates": 1,
        "mode_counts": {"binance_export": 1},
    }
    assert not issues


def test_binance_adapter_extract_wallet_inventory_is_empty() -> None:
    records, issues = BinanceAdapter().extract_wallet_inventory(
        "binance",
        Path("/tmp/raw"),
        build_source_profile(adapter_id="binance"),
    )

    assert not records
    assert not issues


def test_is_no_data_row_detects_binance_sentinel() -> None:
    assert _is_no_data_row({"User ID": "No data matches the criteria."})
    assert not _is_no_data_row({"User ID": "123"})


def test_binance_spot_rows_normalize_buy_and_sell_trades(tmp_path: Path) -> None:
    path = tmp_path / "Binance-Spot-Trade-History-202603230406(UTC--6)_abcd.csv"
    path.write_text(
        "Time,Pair,Side,Price,Executed,Amount,Fee\n"
        "23-03-23 04:06:00,BTCUSDT,BUY,28000,0.001BTC,28USDT,0.01USDT\n"
        "23-03-23 05:06:00,ETHUSDT,SELL,1800,0.5ETH,900USDT,0.02USDT\n",
        encoding="utf-8",
    )

    events = _normalize_spot_rows(build_source_profile(adapter_id="binance"), path)

    assert [event.event_kind for event in events] == ["Trade", "Trade"]
    assert str(events[0].asset_in) == "BTC"
    assert str(events[0].asset_out) == "USDT"
    assert str(events[1].asset_in) == "USDT"
    assert str(events[1].asset_out) == "ETH"
    assert events[0].render_group == "Spot"
    assert events[1].render_group == "Spot"


def test_binance_deposit_and_withdraw_rows_skip_incomplete_entries(tmp_path: Path) -> None:
    deposit_path = tmp_path / "Binance-Deposit-History-202603230411(UTC--6)_abcd.csv"
    deposit_path.write_text(
        "Time,Coin,Network,Amount,Address,TXID,Status\n"
        "23-03-23 04:11:00,USDT,TRX,100,TA1,deposit-tx,Completed\n"
        "23-03-23 04:12:00,USDT,TRX,50,TA2,deposit-pending,Pending\n",
        encoding="utf-8",
    )
    withdraw_path = tmp_path / "Binance-Withdraw-History-202603230412(UTC--6)_abcd.csv"
    withdraw_path.write_text(
        "Time,Coin,Network,Amount,Fee,Address,TXID,Status\n"
        "23-03-23 04:12:00,ETH,ERC20,1.5,0.01,0xabc,withdraw-tx,Completed\n"
        "23-03-23 04:13:00,ETH,ERC20,0.5,0.01,0xdef,withdraw-pending,Pending\n",
        encoding="utf-8",
    )

    deposits = _normalize_deposit_rows(build_source_profile(adapter_id="binance"), deposit_path)
    withdrawals = _normalize_withdraw_rows(build_source_profile(adapter_id="binance"), withdraw_path)

    assert len(deposits) == 1
    assert deposits[0].event_kind == "Deposit"
    assert str(deposits[0].asset_in) == "USDT"
    assert deposits[0].tx_hash == "deposit-tx"
    assert len(withdrawals) == 1
    assert withdrawals[0].event_kind == "Withdrawal"
    assert str(withdrawals[0].asset_out) == "ETH"
    assert str(withdrawals[0].fee_asset) == "ETH"
    assert withdrawals[0].tx_hash == "withdraw-tx"


def test_binance_deposit_and_withdraw_rows_skip_blank_amounts(tmp_path: Path) -> None:
    deposit_path = tmp_path / "Binance-Deposit-History-202603230411(UTC--6)_abcd.csv"
    deposit_path.write_text(
        "Time,Coin,Network,Amount,Address,TXID,Status\n23-03-23 04:11:00,USDT,TRX,,TA1,deposit-tx,Completed\n",
        encoding="utf-8",
    )
    withdraw_path = tmp_path / "Binance-Withdraw-History-202603230412(UTC--6)_abcd.csv"
    withdraw_path.write_text(
        "Time,Coin,Network,Amount,Fee,Address,TXID,Status\n"
        "23-03-23 04:12:00,ETH,ERC20,,0.01,0xabc,withdraw-tx,Completed\n",
        encoding="utf-8",
    )

    assert not _normalize_deposit_rows(build_source_profile(adapter_id="binance"), deposit_path)
    assert not _normalize_withdraw_rows(build_source_profile(adapter_id="binance"), withdraw_path)


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


def test_binance_transaction_history_ignores_no_data_rows_and_maps_staking_rewards(tmp_path: Path) -> None:
    path = tmp_path / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv"
    path.write_text(
        "User ID,Time,Account,Operation,Coin,Change,Remark\n"
        "No data matches the criteria.\n"
        "1,23-03-23 04:00:00,Earn,ETH 2.0 Staking Rewards,ETH,0.005,Reward\n",
        encoding="utf-8",
    )

    events, issues = _normalize_transaction_rows(
        build_source_profile(adapter_id="binance"),
        path,
    )

    assert len(events) == 1
    assert events[0].event_kind == "Staking"
    assert str(events[0].asset_in) == "ETH"
    assert not issues


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

    events, issues = _normalize_transaction_rows(
        build_source_profile(adapter_id="binance"),
        path,
    )

    assert not events
    assert len(issues) == 1
    assert issues[0].kind == "unsupported_group"


def test_binance_helper_functions_cover_fallback_paths() -> None:
    assert _split_pair("DOGEUSDT") == ("DOGE", "USDT")
    assert _split_pair("UNKNOWN") == ("", "")
    assert _amount_with_asset("0.5eth") == (Decimal("0.5"), "ETH")
    assert _amount_with_asset("0.5") == (Decimal("0.5"), "")
    assert _parse_offset_timestamp("23-03-23 04:06:00", "Binance.csv").strftime("%Y-%m-%d %H:%M:%S") == (
        "2023-03-23 04:06:00"
    )
    assert _row_change({"Change": ""}) == Decimal("0")
