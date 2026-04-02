from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.platforms.binance.funding_history import (
    normalize_deposit_rows,
    normalize_withdraw_rows,
)
from tallylot.adapters.sources.platforms.binance.spot_trades import normalize_spot_rows
from tallylot.adapters.support.drafts import compile_activity_drafts
from tests.support.services import build_source_profile


def test_binance_spot_rows_normalize_buy_and_sell_trades(tmp_path: Path) -> None:
    path = tmp_path / "Binance-Spot-Trade-History-202603230406(UTC--6)_abcd.csv"
    path.write_text(
        "Time,Pair,Side,Price,Executed,Amount,Fee\n"
        "23-03-23 04:06:00,BTCUSDT,BUY,28000,0.001BTC,28USDT,0.01USDT\n"
        "23-03-23 05:06:00,ETHUSDT,SELL,1800,0.5ETH,900USDT,0.02USDT\n",
        encoding="utf-8",
    )

    events = compile_activity_drafts(tuple(normalize_spot_rows(build_source_profile(adapter_id="binance"), path)))

    assert [event.category for event in events] == ["trade", "trade"]
    assert str(events[0].asset_in) == "BTC"
    assert str(events[0].asset_out) == "USDT"
    assert str(events[1].asset_in) == "USDT"
    assert str(events[1].asset_out) == "ETH"
    assert events[0].account == "Spot"
    assert events[1].account == "Spot"


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

    deposits = compile_activity_drafts(
        tuple(
            normalize_deposit_rows(
                build_source_profile(adapter_id="binance"),
                deposit_path,
            )
        )
    )
    withdrawals = compile_activity_drafts(
        tuple(normalize_withdraw_rows(build_source_profile(adapter_id="binance"), withdraw_path))
    )

    assert len(deposits) == 1
    assert deposits[0].category == "deposit"
    assert str(deposits[0].asset_in) == "USDT"
    assert deposits[0].tx_hash == "deposit-tx"
    assert len(withdrawals) == 1
    assert withdrawals[0].category == "withdrawal"
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

    assert not normalize_deposit_rows(build_source_profile(adapter_id="binance"), deposit_path)
    assert not normalize_withdraw_rows(build_source_profile(adapter_id="binance"), withdraw_path)
