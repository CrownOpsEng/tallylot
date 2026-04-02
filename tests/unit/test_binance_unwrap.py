from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from tests.support.helpers import read_dict_rows
import binance_unwrap


class BinanceUnwrapTests(unittest.TestCase):
    def test_family_from_name_groups_zip_splits_and_year_splits(self) -> None:
        self.assertEqual(
            "Binance-Futures-Trade-History",
            binance_unwrap.family_from_name(
                Path("Binance-Futures-Trade-History-202603230520(UTC--6)_2b8deebc.csv")
            ),
        )
        self.assertEqual(
            "Binance Transactions",
            binance_unwrap.family_from_name(Path("Binance Transactions 2024.csv")),
        )

    def test_is_no_data_row_detects_binance_sentinel(self) -> None:
        self.assertTrue(
            binance_unwrap.is_no_data_row(
                {
                    "Uid": "No data matches the criteria.",
                    "Time": "",
                    "Order No": "",
                }
            )
        )
        self.assertFalse(
            binance_unwrap.is_no_data_row(
                {
                    "Uid": "123",
                    "Time": "2024-01-01 00:00:00",
                }
            )
        )

    def test_parse_timestamp_handles_utc_suffix_without_separator(self) -> None:
        parsed = binance_unwrap.parse_timestamp("2025-12-31(UTC0)")

        self.assertIsNotNone(parsed)
        self.assertEqual("2025-12-31 00:00:00", parsed.strftime("%Y-%m-%d %H:%M:%S"))

    def test_unwrap_binance_exports_extracts_inventory_and_combines_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
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

            self.assertFalse(first_zip.exists())
            self.assertFalse(second_zip.exists())
            self.assertTrue(extracted_csv.exists())
            self.assertTrue(combined_csv.exists())
            self.assertTrue(inventory_csv.exists())
            self.assertTrue(combined_summary_csv.exists())
            self.assertEqual(2, summary["zip_files_processed"])
            self.assertEqual("2024-01-01 01:02:03", summary["earliest_timestamp"])
            self.assertEqual("2024-09-10 12:09:17", summary["latest_timestamp"])

            combined_rows = read_dict_rows(combined_csv)
            self.assertEqual(1, len(combined_rows))
            self.assertEqual(
                "Binance-Futures-Trade-History-202603230520(UTC--6)_aaaa1111.csv",
                combined_rows[0]["source_file"],
            )

            inventory_rows = read_dict_rows(inventory_csv)
            empty_row = next(
                row
                for row in inventory_rows
                if row["filename"] == "Binance-Futures-Trade-History-202603230521(UTC--6)_bbbb2222.csv"
            )
            self.assertEqual("yes", empty_row["empty_export"])
            combined_summary_rows = read_dict_rows(combined_summary_csv)
            self.assertEqual("2", combined_summary_rows[0]["file_count"])
