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
