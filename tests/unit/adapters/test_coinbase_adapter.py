from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.adapters.sources.coinbase.adapter import CoinbaseAdapter, _money_decimal, _read_retail_rows
from tests.support.services import build_source_profile


def test_coinbase_adapter_reports_missing_retail_csv_as_explicit_issue(tmp_path: Path) -> None:
    result = CoinbaseAdapter().normalize(
        build_source_profile(adapter_id="coinbase", raw_dir=str(tmp_path)),
        tmp_path,
    )

    assert not result.canonical_events
    assert result.issues[0].kind == "missing_required_input"
    assert "retail all-time CSV" in result.issues[0].message


def test_coinbase_adapter_normalizes_buy_row_from_header_detected_csv(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail-export.csv").write_text(
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "tx-1,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,"
        "Bought 0.01 BTC for 610 CAD\n",
        encoding="utf-8",
    )

    result = CoinbaseAdapter().normalize(
        build_source_profile(adapter_id="coinbase", raw_dir=str(raw_dir)),
        raw_dir,
    )

    event = result.canonical_events[0]

    assert len(result.canonical_events) == 1
    assert event.event_kind == "Trade"
    assert str(event.asset_in) == "BTC"
    assert str(event.asset_out) == "CAD"
    assert str(event.amount_in) == "0.01"
    assert event.amount_out == 610


def test_coinbase_adapter_normalizes_sell_and_receive_rows(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail-export.csv").write_text(
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "tx-sell,2024-02-08 16:31:22 UTC,Sell,BTC,0.01000000,CAD,$60000.00,$600.00,$590.00,$10.00,"
        "Sold 0.01 BTC for 590 CAD\n"
        "tx-receive,2024-02-09 10:00:00 UTC,Receive,ETH,1.50000000,CAD,$0.00,$0.00,$0.00,$0.00,"
        "Received ETH\n",
        encoding="utf-8",
    )

    result = CoinbaseAdapter().normalize(
        build_source_profile(adapter_id="coinbase", raw_dir=str(raw_dir)),
        raw_dir,
    )

    sell_event, receive_event = result.canonical_events

    assert len(result.canonical_events) == 2
    assert sell_event.event_kind == "Trade"
    assert str(sell_event.asset_in) == "CAD"
    assert str(sell_event.asset_out) == "BTC"
    assert receive_event.event_kind == "Deposit"
    assert str(receive_event.asset_in) == "ETH"
    assert not result.issues


def test_coinbase_adapter_surfaces_unsupported_rows_without_dropping_supported_rows(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail-export.csv").write_text(
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "tx-1,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,"
        "Bought 0.01 BTC for 610 CAD\n"
        "tx-2,2024-02-10 12:00:00 UTC,Convert,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,"
        "Unsupported convert row\n",
        encoding="utf-8",
    )

    result = CoinbaseAdapter().normalize(
        build_source_profile(adapter_id="coinbase", raw_dir=str(raw_dir)),
        raw_dir,
    )

    assert len(result.canonical_events) == 1
    assert result.canonical_events[0].event_kind == "Trade"
    assert len(result.issues) == 1
    assert result.issues[0].kind == "unsupported_row"


def test_coinbase_retail_row_reader_skips_preface_lines(tmp_path: Path) -> None:
    path = tmp_path / "coinbase.csv"
    path.write_text(
        "\nTransactions\nUser,Example,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "raw-1,2025-01-01 00:00:00 UTC,Reward Income,ADA,1.0,CAD,$1.00,$1.00,$1.00,$0.00,Received 1 ADA\n",
        encoding="utf-8",
    )

    rows = _read_retail_rows(path)

    assert len(rows) == 1
    assert rows[0]["ID"] == "raw-1"


def test_coinbase_money_decimal_parses_currency_text() -> None:
    assert _money_decimal("$1,234.56") == Decimal("1234.56")


def test_coinbase_adapter_normalizes_reward_income_and_asset_migration_pair(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail-export.csv").write_text(
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "reward-1,2023-03-18 01:28:49 UTC,Reward Income,ADA,0.000021,CAD,$0.48,$0.00,$0.00,$0.00,"
        "Received 0.000021 ADA from Coinbase Rewards\n"
        "migration-neg,2025-10-17 13:38:17 UTC,Asset Migration,MATIC,-1.65526374,CAD,$0.25,-$0.42,-$0.42,$0.00,\n"
        "migration-pos,2025-10-17 13:38:17 UTC,Asset Migration,POL,1.65526374,CAD,$0.25,$0.42,$0.42,$0.00,\n",
        encoding="utf-8",
    )

    result = CoinbaseAdapter().normalize(
        build_source_profile(adapter_id="coinbase", raw_dir=str(raw_dir)),
        raw_dir,
    )

    reward_event, migration_event = result.canonical_events

    assert len(result.canonical_events) == 2
    assert reward_event.event_kind == "Interest Income"
    assert str(reward_event.asset_in) == "ADA"
    assert migration_event.event_kind == "Swap (non taxable)"
    assert migration_event.render_group == "Asset Migration"
    assert str(migration_event.asset_in) == "POL"
    assert str(migration_event.asset_out) == "MATIC"
    assert not result.issues
