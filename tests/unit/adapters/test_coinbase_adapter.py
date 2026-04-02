from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.adapters.sources.coinbase.adapter import CoinbaseAdapter
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
