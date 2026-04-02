from __future__ import annotations

import zipfile
from pathlib import Path

import binance_unwrap
from tests.support.helpers import read_dict_rows


def test_family_from_name_groups_zip_splits_and_year_splits() -> None:
    assert binance_unwrap.family_from_name(
        Path("Binance-Futures-Trade-History-202603230520(UTC--6)_2b8deebc.csv")
    ) == "Binance-Futures-Trade-History"
    assert binance_unwrap.family_from_name(Path("Binance Transactions 2024.csv")) == "Binance Transactions"


def test_is_no_data_row_detects_binance_sentinel() -> None:
    assert binance_unwrap.is_no_data_row(
        {
            "Uid": "No data matches the criteria.",
            "Time": "",
            "Order No": "",
        }
    )
    assert not binance_unwrap.is_no_data_row(
        {
            "Uid": "123",
            "Time": "2024-01-01 00:00:00",
        }
    )


def test_parse_timestamp_handles_utc_suffix_without_separator() -> None:
    parsed = binance_unwrap.parse_timestamp("2025-12-31(UTC0)")

    assert parsed is not None
    assert parsed.strftime("%Y-%m-%d %H:%M:%S") == "2025-12-31 00:00:00"


def test_parse_timestamp_applies_source_timezone() -> None:
    parsed = binance_unwrap.parse_timestamp(
        "2024-01-01 01:02:03",
        source_timezone=binance_unwrap.source_timezone_from_filename("Binance-Futures-Trade-History-202603230520(UTC--6)_aaaa1111.csv"),
    )

    assert parsed is not None
    assert parsed.strftime("%Y-%m-%d %H:%M:%S") == "2024-01-01 07:02:03"


def test_unwrap_binance_exports_extracts_inventory_and_combines_rows(tmp_path: Path) -> None:
    repo_root = tmp_path
    source_dir = repo_root / "01_raw_exports" / "external" / "binance" / "raw"
    normalized_dir = repo_root / "02_working" / "normalized"
    source_dir.mkdir(parents=True)
    normalized_dir.mkdir(parents=True)

    yearly_csv = source_dir / "Binance Transactions 2024.csv"
    yearly_csv.write_text(
        "User ID,Time,Account,Operation,Coin,Change,Remark\n"
        "1,2024-09-10 12:09:17,Spot,Deposit,USDT,10,test\n",
        encoding="utf-8",
    )

    first_zip = source_dir / "Binance-Futures-Trade-History-202603230520(UTC--6)_aaaa1111.zip"
    second_zip = source_dir / "Binance-Futures-Trade-History-202603230521(UTC--6)_bbbb2222.zip"
    with zipfile.ZipFile(first_zip, "w") as archive:
        archive.writestr(
            "Binance-Futures-Trade-History-202603230520(UTC--6).csv",
            (
                "Uid,Time,Symbol,Side,Price,Quantity,Amount,Fee,Realized Profit,Buyer,Maker,Trade ID,Order ID\n"
                "99,2024-01-01 01:02:03,BTCUSDT,BUY,40000,0.01,400,0.4,0,Y,N,trade-1,order-1\n"
            ),
        )
    with zipfile.ZipFile(second_zip, "w") as archive:
        archive.writestr(
            "Binance-Futures-Trade-History-202603230521(UTC--6).csv",
            (
                "Uid,Time,Symbol,Side,Price,Quantity,Amount,Fee,Realized Profit,Buyer,Maker,Trade ID,Order ID\n"
                "No data matches the criteria.\n"
            ),
        )

    summary = binance_unwrap.unwrap_binance_exports(
        source_dir,
        normalized_dir=normalized_dir,
        delete_zips=True,
    )

    extracted_csv = source_dir / "Binance-Futures-Trade-History-202603230520(UTC--6)_aaaa1111.csv"
    combined_csv = normalized_dir / "binance" / "combined" / "binance_futures_trade_history_combined.csv"
    inventory_csv = source_dir.parent / "raw_csv_inventory.csv"
    combined_summary_csv = normalized_dir / "binance" / "combined_summary.csv"

    assert not first_zip.exists()
    assert not second_zip.exists()
    assert extracted_csv.exists()
    assert combined_csv.exists()
    assert inventory_csv.exists()
    assert combined_summary_csv.exists()
    assert summary["zip_files_processed"] == 2
    assert summary["earliest_timestamp"] == "2024-01-01 07:02:03"
    assert summary["latest_timestamp"] == "2024-09-10 12:09:17"

    combined_rows = read_dict_rows(combined_csv)
    assert len(combined_rows) == 1
    assert combined_rows[0]["source_file"] == "Binance-Futures-Trade-History-202603230520(UTC--6)_aaaa1111.csv"

    inventory_rows = read_dict_rows(inventory_csv)
    empty_row = next(
        row
        for row in inventory_rows
        if row["filename"] == "Binance-Futures-Trade-History-202603230521(UTC--6)_bbbb2222.csv"
    )
    assert empty_row["empty_export"] == "yes"

    combined_summary_rows = read_dict_rows(combined_summary_csv)
    assert combined_summary_rows[0]["file_count"] == "2"
