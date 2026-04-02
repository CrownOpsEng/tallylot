from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from tallylot.adapters.sources.platforms.coinbase.retail_csv import read_retail_rows
from tallylot.adapters.sources.platforms.coinbase.retail_rows import money_decimal


def test_coinbase_retail_row_reader_skips_preface_lines(tmp_path: Path) -> None:
    path = tmp_path / "coinbase.csv"
    path.write_text(
        "\nTransactions\nUser,Example,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "raw-1,2025-01-01 00:00:00 UTC,Reward Income,ADA,1.0,CAD,$1.00,$1.00,$1.00,$0.00,Received 1 ADA\n",
        encoding="utf-8",
    )

    rows = read_retail_rows(path)

    assert len(rows) == 1
    assert rows[0]["ID"] == "raw-1"


def test_coinbase_money_decimal_parses_currency_text() -> None:
    assert money_decimal("$1,234.56") == Decimal("1234.56")
