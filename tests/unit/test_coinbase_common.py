from __future__ import annotations

from pathlib import Path

import coinbase_common


def test_coinbase_timestamp_parsers_preserve_utc_clock_time() -> None:
    retail = coinbase_common.parse_coinbase_retail_timestamp("2025-10-17 13:38:17 UTC")
    pro = coinbase_common.parse_coinbase_pro_timestamp("2021-05-10T02:37:18.000Z")

    assert retail.strftime("%Y-%m-%d %H:%M:%S") == "2025-10-17 13:38:17"
    assert pro.strftime("%Y-%m-%d %H:%M:%S") == "2021-05-10 02:37:18"


def test_retail_csv_rows_skips_preface_and_reads_transactions(tmp_path: Path) -> None:
    path = tmp_path / "coinbase.csv"
    path.write_text(
        "\nTransactions\nUser,Example,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "raw-1,2025-01-01 00:00:00 UTC,Reward Income,ADA,1.0,CAD,$1.00,$1.00,$1.00,$0.00,Received 1 ADA\n",
        encoding="utf-8",
    )

    rows = coinbase_common.retail_csv_rows(path)

    assert len(rows) == 1
    assert rows[0]["ID"] == "raw-1"


def test_normalize_coinbase_transactions_builds_expected_shapes() -> None:
    retail_rows = [
        {
            "ID": "buy-1",
            "Timestamp": "2019-09-11 01:06:35 UTC",
            "Transaction Type": "Buy",
            "Asset": "BTC",
            "Quantity Transacted": "0.0017564",
            "Price Currency": "CAD",
            "Price at Transaction": "$13,396.9183875",
            "Subtotal": "$23.53035",
            "Total (inclusive of fees and/or spread)": "$25.00",
            "Fees and/or Spread": "$1.469652544195",
            "Notes": "Bought 0.0017564 BTC for 25 CAD using 1234",
        },
        {
            "ID": "send-1",
            "Timestamp": "2019-10-30 00:38:57 UTC",
            "Transaction Type": "Send",
            "Asset": "ETH",
            "Quantity Transacted": "-0.055165",
            "Price Currency": "CAD",
            "Price at Transaction": "$249.80",
            "Subtotal": "-$13.78",
            "Total (inclusive of fees and/or spread)": "-$13.78",
            "Fees and/or Spread": "$0.00",
            "Notes": "Sent 0.055165 ETH to 0xabc (to 0xabc)",
        },
        {
            "ID": "reward-1",
            "Timestamp": "2023-03-18 01:28:49 UTC",
            "Transaction Type": "Reward Income",
            "Asset": "ADA",
            "Quantity Transacted": "0.000021",
            "Price Currency": "CAD",
            "Price at Transaction": "$0.48",
            "Subtotal": "$0.00",
            "Total (inclusive of fees and/or spread)": "$0.00",
            "Fees and/or Spread": "$0.00",
            "Notes": "Received 0.000021 ADA from Coinbase Rewards",
        },
        {
            "ID": "migration-neg",
            "Timestamp": "2025-10-17 13:38:17 UTC",
            "Transaction Type": "Asset Migration",
            "Asset": "MATIC",
            "Quantity Transacted": "-1.65526374",
            "Price Currency": "CAD",
            "Price at Transaction": "$0.25",
            "Subtotal": "-$0.42",
            "Total (inclusive of fees and/or spread)": "-$0.42",
            "Fees and/or Spread": "$0.00",
            "Notes": "",
        },
        {
            "ID": "migration-pos",
            "Timestamp": "2025-10-17 13:38:17 UTC",
            "Transaction Type": "Asset Migration",
            "Asset": "POL",
            "Quantity Transacted": "1.65526374",
            "Price Currency": "CAD",
            "Price at Transaction": "$0.25",
            "Subtotal": "$0.42",
            "Total (inclusive of fees and/or spread)": "$0.42",
            "Fees and/or Spread": "$0.00",
            "Notes": "",
        },
    ]

    rows = coinbase_common.normalize_coinbase_transactions(
        retail_rows,
        pro_statement_rows=[],
        pro_fill_rows=[],
        retail_source=Path("coinbase.csv"),
    )

    assert len(rows) == 4
    assert rows[0]["Type"] == "Trade"
    assert rows[0]["Buy Cur."] == "BTC"
    assert rows[1]["Type"] == "Withdrawal"
    assert rows[1]["allowed_types"] == "Withdrawal|Spend"
    assert rows[2]["Type"] == "Interest Income"
    assert rows[3]["Type"] == "Swap (non taxable)"
    assert rows[3]["Group"] == "Asset Migration"


def test_coinbase_balance_rows_from_text_extracts_cash_and_assets() -> None:
    text = """
    Cash Balances Closing Balance 0 CAD as of 2026-03-22 23:59:59 UTC
    Portfolio summary balances are as of 2026-03-22 23:59:59 UTC
    ADA 0.080457 N/A 0.34390493 CAD/ADA 0.03 CAD
    POL 1.65526374 N/A 0.12634783 CAD/POL 0.21 CAD
    """

    rows = coinbase_common.coinbase_balance_rows_from_text(text, "statement.pdf")

    assert len(rows) == 3
    assert rows[0]["balance_kind"] == "cash_closing_balance"
    assert rows[1]["asset"] == "ADA"
    assert rows[2]["asset"] == "POL"
