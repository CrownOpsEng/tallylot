from __future__ import annotations

from pathlib import Path

from tallylot.application.profiling.inventory import inventory_file_details


def test_inventory_file_details_applies_binance_filename_offset_to_min_and_max(tmp_path: Path) -> None:
    path = tmp_path / "Binance-Spot-Trade-History-202603230406(UTC--6)_abcd.csv"
    path.write_text(
        "Time,Pair,Side,Price,Executed,Amount,Fee\n"
        "23-09-20 18:20:55,ALGOUSDT,SELL,0.0997,103ALGO,10.2691USDT,0.00003593BNB\n"
        "23-09-20 19:20:55,ALGOUSDT,SELL,0.0997,103ALGO,10.2691USDT,0.00003593BNB\n",
        encoding="utf-8",
    )

    _, row_count, details = inventory_file_details(path)

    assert row_count == 2
    assert details.min_timestamp == "2023-09-21 00:20:55"
    assert details.max_timestamp == "2023-09-21 01:20:55"
    assert details.timezone_mode == "filename_offset"
    assert details.timezone_value == "UTC-06:00"


def test_inventory_file_details_detects_header_utc_and_date_only_modes(tmp_path: Path) -> None:
    utc_path = tmp_path / "crypto_transactions.csv"
    utc_path.write_text(
        "Timestamp (UTC),Amount\n2021-07-06 17:37:09,1\n",
        encoding="utf-8",
    )
    date_only_path = tmp_path / "activities-export.csv"
    date_only_path.write_text(
        "transaction_date,settlement_date,account_type\n2021-05-09,,Crypto\n",
        encoding="utf-8",
    )

    _, _, utc_details = inventory_file_details(utc_path)
    _, _, date_only_details = inventory_file_details(date_only_path)

    assert utc_details.timezone_mode == "header_utc"
    assert utc_details.timezone_value == "UTC"
    assert utc_details.min_timestamp == "2021-07-06 17:37:09"
    assert date_only_details.timezone_mode == "date_only"
    assert date_only_details.timestamp_resolution == "date_only"
    assert date_only_details.min_timestamp == "2021-05-09 00:00:00"


def test_inventory_file_details_ignores_placeholder_no_data_rows(tmp_path: Path) -> None:
    path = tmp_path / "Binance-Futures-Order-History-202603230503(UTC--6)_abcd.csv"
    path.write_text(
        "Uid,Time,Order No\nNo data matches the criteria.\n",
        encoding="utf-8",
    )

    _, row_count, details = inventory_file_details(path)

    assert row_count == 0
    assert details.date_field == "Time"
    assert details.min_timestamp == ""
    assert details.timezone_mode == ""


def test_inventory_file_details_skips_coinbase_retail_preamble_rows(tmp_path: Path) -> None:
    path = tmp_path / "retail-export.csv"
    path.write_text(
        "\n"
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,"
        "Price Currency,Price at Transaction,Subtotal,"
        "Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "tx-1,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,"
        "$60000.00,$600.00,$610.00,$10.00,Bought 0.01 BTC for 610 CAD\n",
        encoding="utf-8",
    )

    header, row_count, details = inventory_file_details(path)

    assert header[0] == "ID"
    assert "Timestamp" in header
    assert row_count == 1
    assert details.date_field == "Timestamp"
    assert details.min_timestamp == "2024-02-08 16:31:22"
    assert details.timezone_mode == "value_utc"
